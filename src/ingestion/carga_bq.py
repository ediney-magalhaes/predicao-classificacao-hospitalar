"""
Carga de dados anonimizados no BigQuery.

Este módulo faz append incremental na tabela Bronze.
Cada execução adiciona registros novos — nunca sobrescreve.

A tabela destino e o projeto GCP vêm do settings.py.
"""

from datetime import datetime, timezone

import pandas as pd
import pandas_gbq
from google.oauth2 import service_account

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

    # acrescenta ao banco existente
    pandas_gbq.to_gbq(
        dataframe=df,
        destination_table=destino,
        project_id=settings.gcp_project_id,
        credentials=credenciais,
        if_exists="append"
    )
    return len(df)