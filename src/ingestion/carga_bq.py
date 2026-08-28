"""
Carga de dados anonimizados no BigQuery.

Este módulo faz append incremental na tabela Bronze.
Cada execução adiciona registros novos — nunca sobrescreve.

A tabela destino e o projeto GCP vêm do settings.py.
"""

import pandas as pd
import pandas_gbq
from google.oauth2 import service_account
from google.cloud import bigquery
from datetime import datetime, timezone
from config.settings import settings

def enviar_para_bigquery(df: pd.DataFrame, safra_mes: str, tabela_destino: str | None = None) -> int:
    """
    Faz append de um DataFrame anonimizado na tabela Bronze do BigQuery.

    Args:
        df: DataFrame já anonimizado e validado.
        safra_mes: Identificador da safra no formato 'YYYY-MM' (ex: '2026-04').
        tabela_destino: Tabela no BigQuery (dataset.tabela).
                        Se None, usa settings.bq_tabela_bronze.

    Returns:
        Número de registros enviados.
    """
    # cria uma cópia do DataSet para trabalhar
    df = df.copy()

    # adiciona metadados para rastreabilidade
    df["safra_mes"] = safra_mes
    df["data_ingestao"] = datetime.now(timezone.utc).isoformat()

    # cria credenciais do GCP
    credenciais = service_account.Credentials.from_service_account_file(settings.google_application_credentials)

    # tabela de destino
    destino = tabela_destino or settings.bq_tabela_bronze

    # remove safra anterior se existir (idempotência: reprocessar não duplica)
    client = bigquery.Client(credentials=credenciais, project=settings.gcp_project_id)
    delete_query = f"DELETE FROM `{destino}` WHERE safra_mes = '{safra_mes}'"
    client.query(delete_query).result()

    # acrescenta ao banco existente
    pandas_gbq.to_gbq(
        dataframe=df,
        destination_table=destino,
        project_id=settings.gcp_project_id,
        credentials=credenciais,
        if_exists="append"
    )
    return len(df)

def enviar_para_bigquery_merge(df_valor_conta:pd.DataFrame) -> int:
    tabela_staging = "ml-classificacao-sus.dados_saidas_hospitalares.bronze_financeiro_staging_load"
    tabela_destino = "ml-classificacao-sus.dados_saidas_hospitalares.bronze_financeiro_anonimizado"

    # cria uma cópia do DataFrame
    df_valor_conta = df_valor_conta.copy()
    # adiciona coluna de metadado sobre a ingestão
    df_valor_conta["data_ingestao"] = datetime.now(timezone.utc).isoformat()

    # cria crendenciais de conexão
    credenciais = service_account.Credentials.from_service_account_file(settings.google_application_credentials)

    # envia ao banco existente
    pandas_gbq.to_gbq(
        dataframe=df_valor_conta,
        destination_table=tabela_staging,
        project_id=settings.gcp_project_id,
        credentials=credenciais,
        if_exists='replace'
    )

    # aplicando merge
    query_merge = f"""
    MERGE {tabela_destino} as destino
    USING {tabela_staging} as staging
    ON destino.nr_interno_conta = staging.nr_interno_conta AND destino.mes_ano_producao = staging.mes_ano_producao
    WHEN MATCHED THEN
    UPDATE SET
        nr_atendimento = staging.nr_atendimento,
        ano_producao = staging.ano_producao,
        valor = staging.valor,
        convenio = staging.convenio,
        hash_paciente = staging.hash_paciente,
        valor_recebido = staging.valor_recebido,
        valor_glosa = staging.valor_glosa,
        data_ingestao = staging.data_ingestao
    WHEN NOT MATCHED THEN
    INSERT (
        nr_interno_conta,
        mes_ano_producao,
        nr_atendimento,
        ano_producao,
        valor,
        convenio,
        hash_paciente,
        valor_recebido,
        valor_glosa,
        data_ingestao
    )
    VALUES (
        staging.nr_interno_conta,
        staging.mes_ano_producao,
        staging.nr_atendimento,
        staging.ano_producao,
        staging.valor,
        staging.convenio,
        staging.hash_paciente,
        staging.valor_recebido,
        staging.valor_glosa,
        staging.data_ingestao
    )
    """
    # conexão com bigquery
    cliente = bigquery.Client(credentials=credenciais, project=settings.gcp_project_id)

    # execução da query
    job = cliente.query(query_merge)
    job.result()
    total_afetado = job.num_dml_affected_rows

    return total_afetado
    