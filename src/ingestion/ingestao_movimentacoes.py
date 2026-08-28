"""
Ingestão do relatório de movimentações internas (fonte de dado para UTI).

Fluxo:
  1. Reconstrói o layout do relatório bruto (colunas desconfiguradas)
  2. Valida o relatório reconstruído (Pandera)
  3. Anonimiza (hash do nome do paciente)
  4. Envia para bronze_movimentacoes_anonimizado (append)

Diferente do pipeline_correcao.py (HITL), este fluxo não envolve
comparação com predição nem revisão humana — é ingestão direta de
uma fonte de dado operacional do hospital, usada exclusivamente
para reconstruir, via dbt, a passagem de cada atendimento por UTI.

Chamado a partir do app.py, na mesma aba de "Enviar Correções",
já que a assistente sobe as duas planilhas no mesmo momento mensal.
"""

import logging

import pandas as pd

from src.validacao.schemas_movimentacoes import validar_movimentacoes
from src.ingestion.anonimizacao import anonimizar_dataframe
from src.ingestion.carga_bq import enviar_para_bigquery
from src.ingestion.preprocessamento_movimentacoes import reconstruir_layout_movimentacoes
from config.settings import settings

logger = logging.getLogger(__name__)

def processar_movimentacoes(
    df_movimentacoes: pd.DataFrame,
    safra_mes: str,
) -> dict:
    """
    Processa o relatório de movimentações: reconstrói, valida, anonimiza, ingere.

    Args:
        df_movimentacoes: DataFrame bruto do relatório de movimentações
            (lido com header=None, layout desconfigurado do sistema).
        safra_mes: Mês de referência no formato 'YYYY-MM'.

    Returns:
        Dicionário com:
        {
            "sucesso": bool,
            "etapa_falha": str ou None,
            "mensagem": str,
            "registros_enviados": int ou None,
        }
    """
    resultado = {
        "sucesso": False,
        "etapa_falha": None,
        "mensagem": "",
        "registros_enviados": None,
    }

    # ETAPA 1: Reconstrução do layout (arquivo bruto vem desconfigurado)
    logger.info(f"Iniciando processamento de movimentações para safra {safra_mes}")

    try:
        df_movimentacoes = reconstruir_layout_movimentacoes(df_movimentacoes)
    except Exception as e:
        resultado["etapa_falha"] = "reconstrução de layout"
        resultado["mensagem"] = f"Erro ao reconstruir layout do relatório: {e}"
        logger.exception("Falha na reconstrução de layout")
        return resultado

    # ETAPA 2: Validação
    valido, msg_validacao = validar_movimentacoes(df_movimentacoes)
    if not valido:
        resultado["etapa_falha"] = "validação"
        resultado["mensagem"] = msg_validacao
        logger.warning(f"Validação falhou: {msg_validacao}")
        return resultado

    # ETAPA 3: Anonimização
    try:
        df_anonimizado = anonimizar_dataframe(df_movimentacoes)
        logger.info(f"Anonimização concluída: {len(df_anonimizado)} registros")
    except Exception as e:
        resultado["etapa_falha"] = "anonimização"
        resultado["mensagem"] = f"Erro na anonimização: {e}"
        logger.exception("Falha na anonimização")
        return resultado

    # ETAPA 4: Envio para Bronze de movimentações
    try:
        qtd = enviar_para_bigquery(
            df_anonimizado,
            safra_mes,
            tabela_destino=settings.bq_tabela_movimentacoes,
        )
        resultado["registros_enviados"] = qtd
        logger.info(f"{qtd} registros enviados para Bronze de movimentações")
    except Exception as e:
        resultado["etapa_falha"] = "ingestão"
        resultado["mensagem"] = f"Erro ao enviar para BigQuery: {e}"
        logger.exception("Falha na ingestão")
        return resultado

    resultado["sucesso"] = True
    resultado["mensagem"] = (
        f"Movimentações processadas com sucesso. "
        f"{qtd} registros enviados para a Bronze."
    )
    logger.info(f"Ingestão de movimentações concluída para safra {safra_mes}")

    return resultado