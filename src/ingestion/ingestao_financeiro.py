import logging

import pandas as pd

from src.validacao.schemas_financeiro import validar_contas
from src.ingestion.anonimizacao import anonimizar_dataframe
from src.ingestion.carga_bq import enviar_para_bigquery_merge
from config.settings import settings

logger = logging.getLogger(__name__)

def processar_valor_conta(df_valor_conta: pd.DataFrame) -> dict:
    manter_colunas = [
        "NR_ATENDIMENTO",
        "NR_INTERNO_CONTA",
        "MES_ANO_PRODUCAO",
        "ANO_PRODUCAO",
        "VALOR",
        "CONVENIO",
        "PACIENTE",
        "VALOR RECEBIDO",
        "VALOR GLOSA"
    ]

    # filtrar Dataframe conforme colunas mantidas
    df_valor_conta = df_valor_conta[manter_colunas]

    # variável para guardar o resultado final do processamento
    resultado = {
        "sucesso": False,
        "etapa_falha": None,
        "mensagem": "",
        "registros_enviados": None,
    }

    # ETAPA 1: Validação
    valido, msg_validacao = validar_contas(df_valor_conta)
    if not valido:
        resultado["etapa_falha"] = "validação"
        resultado["mensagem"] = msg_validacao
        logger.warning(f"Validação falhou: {msg_validacao}")
        return resultado

    # ETAPA 2: Anonimização
    try:
        df_anonimizado = anonimizar_dataframe(df_valor_conta)
        logger.info(f"Anonimização concluída: {len(df_anonimizado)} registros")
    except Exception as e:
        resultado["etapa_falha"] = "anonimização"
        resultado["mensagem"] = f"Erro na anonimização: {e}"
        logger.exception("Falha na anonimização")
        return resultado

    # Etapa 3: Envio pro BigQuery
    try:
        qtd = enviar_para_bigquery_merge(df_anonimizado)
        logger.info(f"{qtd} registros foram afetados e enviados ao BigQuery")
    except Exception as e:
        resultado["etapa_falha"] = "envio"
        resultado["mensagem"] = f"Erro no envio: {e}"
        logger.exception("Falha no envio ao BigQuery")
        return resultado

    resultado["sucesso"] = True
    resultado["registros_enviados"] = qtd
    resultado["mensagem"] = (
            f"Dados financeiros processados com sucesso. "
            f"{qtd} registros enviados para a Bronze."
        )
    logger.info(f"Sucesso! {qtd} registros enviados ao armazenamento!")
    return resultado