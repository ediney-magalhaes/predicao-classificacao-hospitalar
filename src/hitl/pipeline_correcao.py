"""
Pipeline de processamento de correções humanas (HITL).

Orquestra o fluxo completo pós-revisão:
  1. Valida a planilha revisada (Pandera)
  2. Localiza a predição original na W:
  3. Compara original vs revisada (taxa de correção)
  4. Anonimiza dados sensíveis
  5. Envia para Bronze no BigQuery (append)
  6. Registra evento de auditoria

Quem chama este módulo (app.py, script, teste) não precisa conhecer
os passos internos — só chama processar_correcao() e recebe o resultado.

"""

import logging
from pathlib import Path

import pandas as pd

from config.settings import settings
from src.validacao.schemas_pos_revisao import (
    validar_planilha_revisada,
    normalizar_colunas_revisao,
)
from src.hitl.comparador import calcular_diferencas
from src.hitl.auditoria import registrar_evento_hitl
from src.ingestion.anonimizacao import anonimizar_dataframe
from src.ingestion.carga_bq import enviar_para_bigquery
from src.preprocessing.preparo_ml import engenharia_features

logger = logging.getLogger(__name__)

# mapeamento de número do mês para nome em português
_MESES_PT = {
    "01": "Janeiro", "02": "Fevereiro", "03": "Março",
    "04": "Abril", "05": "Maio", "06": "Junho",
    "07": "Julho", "08": "Agosto", "09": "Setembro",
    "10": "Outubro", "11": "Novembro", "12": "Dezembro",
}

def _localizar_predicao_original(safra_mes: str) -> Path | None:
    """
    Busca o arquivo de predição original na W: pelo mês de referência.

    Convenção de nomes (ADR-0003):
      W:/.../Epidemio/{ano}/Banco Epidemio - {Mês} {Ano} - PREDICAO.xlsx

    Args:
        safra_mes: Mês no formato 'YYYY-MM' (ex: '2026-04').

    Returns:
        Path do arquivo se encontrado, None se não existir.
    """
    ano, mes_num = safra_mes.split("-")

    nome_mes = _MESES_PT.get(mes_num)
    if not nome_mes:
        logger.error(f"Mês inválido na safra: {safra_mes}")
        return None

    nome_arquivo = (
        f"Banco Epidemio - {nome_mes} {ano}"
        f"{settings.sufixo_predicao_original}.xlsx"
    )
    caminho = settings.storage_base_path / ano / nome_arquivo

    if caminho.exists():
        logger.info(f"Predição original encontrada: {caminho}")
        return caminho

    logger.warning(f"Predição original não encontrada: {caminho}")
    return None

def salvar_predicao_original(df: pd.DataFrame, safra_mes: str) -> Path | None:
    """
    Salva a predição original (antes da revisão) na W:.

    Chamada pela aba 1 do app.py logo após gerar predições.
    O arquivo salvo aqui será lido pela aba 2 para comparação.

    Args:
        df: DataFrame com as predições geradas pelo modelo.
        safra_mes: Mês no formato 'YYYY-MM'.

    Returns:
        Path do arquivo salvo, ou None se falhar.
    """
    ano, mes_num = safra_mes.split("-")

    nome_mes = _MESES_PT.get(mes_num)
    if not nome_mes:
        logger.error(f"Mês inválido na safra: {safra_mes}")
        return None

    pasta_ano = settings.storage_base_path / ano
    pasta_ano.mkdir(parents=True, exist_ok=True)

    nome_arquivo = (
        f"Banco Epidemio - {nome_mes} {ano}"
        f"{settings.sufixo_predicao_original}.xlsx"
    )
    caminho = pasta_ano / nome_arquivo

    try:
        df.to_excel(caminho, index=False, engine="openpyxl")
        logger.info(f"Predição original salva em: {caminho}")
        return caminho
    except Exception as e:
        logger.exception(f"Erro ao salvar predição original: {e}")
        return None
    

def processar_correcao(
    df_revisado: pd.DataFrame,
    safra_mes: str,
    revisor: str = "assistente_epidemio",
    tempo_revisao_min: int | None = None,
) -> dict:
    """
    Processa a planilha revisada: valida, compara, anonimiza, ingere, audita.

    Este é o ponto de entrada único para o ciclo HITL. Quem chama
    (app.py, script, teste) recebe um dicionário para exibir o resultado.

    Args:
        df_revisado: DataFrame da planilha corrigida pela assistente.
        safra_mes: Mês de referência no formato 'YYYY-MM'.
        revisor: Identificador de quem revisou.
        tempo_revisao_min: Tempo estimado de revisão em minutos.

    Returns:
        Dicionário com:
        {
            "sucesso": bool,
            "etapa_falha": str ou None,
            "mensagem": str,
            "metricas": dict ou None,
            "registros_enviados": int ou None,
            "evento_auditoria": dict ou None,
        }
    """
    resultado = {
        "sucesso": False,
        "etapa_falha": None,
        "mensagem": "",
        "metricas": None,
        "registros_enviados": None,
        "evento_auditoria": None,
    }

    # ETAPA 1: Validação pós-revisão
    logger.info(f"Iniciando processamento de correção para safra {safra_mes}")

    valido, msg_validacao = validar_planilha_revisada(df_revisado)
    if not valido:
        resultado["etapa_falha"] = "validação"
        resultado["mensagem"] = msg_validacao
        logger.warning(f"Validação falhou: {msg_validacao}")
        return resultado

    # normaliza os valores confirmados como válidos
    df_revisado = normalizar_colunas_revisao(df_revisado)

    # ETAPA 2: Localizar e comparar com predição original
    caminho_original = _localizar_predicao_original(safra_mes)

    if caminho_original:
        df_original = pd.read_excel(caminho_original)
        df_original = normalizar_colunas_revisao(df_original)
        metricas = calcular_diferencas(df_original, df_revisado)
        resultado["metricas"] = metricas
        logger.info(
            f"Comparação concluída: {metricas.get('correcoes_grupo', 0)} "
            f"correções em Grupo, {metricas.get('correcoes_complexidade', 0)} "
            f"em Complexidade"
        )
    else:
        logger.warning(
            f"Predição original não encontrada para {safra_mes}. "
            f"Comparação será ignorada — ingestão prossegue sem métricas."
        )
        metricas = {}

    # ETAPA 3: Anonimização
    try:
        # renomeia colunas de predição para o padrão da Bronze
        df_revisado = df_revisado.rename(columns={
            "PREVISAO_GRUPO": "GRUPO_SUS",
            "PREVISAO_COMPLEXIDADE": "COMPLEXIDADE_SUS",
        })

        # enriquecimento CID: merge com dicionário traz capitulo_breve e grupo_cid remove colunas do dicionário CID se já existirem
        colunas_cid = ["CAPÍTULO BREVE", "GRUPO", "CÓDIGO CID"]
        df_revisado = df_revisado.drop(
            columns=[c for c in colunas_cid if c in df_revisado.columns]
        )
        df_revisado = engenharia_features(df_revisado)
        # normalização de nomes
        df_anonimizado = anonimizar_dataframe(df_revisado)
        logger.info(f"Anonimização concluída: {len(df_anonimizado)} registros")
    except Exception as e:
        resultado["etapa_falha"] = "anonimização"
        resultado["mensagem"] = f"Erro na anonimização: {e}"
        logger.exception("Falha na anonimização")
        return resultado

    # ETAPA 4: Adicionar metadados e enviar pra Bronze
    try:
        qtd = enviar_para_bigquery(df_anonimizado, safra_mes)
        resultado["registros_enviados"] = qtd
        logger.info(f"{qtd} registros enviados para Bronze")
    except Exception as e:
        resultado["etapa_falha"] = "ingestão"
        resultado["mensagem"] = f"Erro ao enviar para BigQuery: {e}"
        logger.exception("Falha na ingestão")
        return resultado

    # ETAPA 5: Registrar auditoria
    try:
        evento = registrar_evento_hitl(
            df_original=pd.read_excel(caminho_original) if caminho_original else df_revisado,
            df_revisado=df_revisado,
            metricas=metricas,
            safra_mes=safra_mes,
            revisor=revisor,
            tempo_revisao_min=tempo_revisao_min,
        )
        resultado["evento_auditoria"] = evento
        logger.info("Evento de auditoria registrado")
    except Exception as e:
        # auditoria falhou, mas os dados já foram ingeridos
        # log do erro mas não reverte a ingestão
        resultado["etapa_falha"] = "auditoria (não-fatal)"
        logger.exception("Falha ao registrar auditoria (dados já ingeridos)")

    # FINAL
    resultado["sucesso"] = True
    resultado["mensagem"] = (
        f"Correção processada com sucesso. "
        f"{resultado['registros_enviados']} registros enviados para a base de treino."
    )
    logger.info(f"Pipeline HITL concluído para safra {safra_mes}")

    return resultado