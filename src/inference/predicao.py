"""
Módulo de Inferência — Predição, Confiança e Business Rule Override.

RESPONSABILIDADES:
    1. Carregar modelos LightGBM com cache (evita recarregar a cada chamada)
    2. Gerar predições de GRUPO_SUS e COMPLEXIDADE_SUS
    3. Calcular confiança (max predict_proba) por predição
    4. Aplicar Business Rule Override (cirurgia → cirúrgico)

PRINCÍPIO DE DESIGN:
    Este módulo NÃO sabe de onde vêm os dados (terminal, GUI, API).
    Recebe DataFrames, devolve DataFrames. Quem faz I/O é o chamador.

USO:
    from src.inference.predicao import gerar_predicoes
    resultado = gerar_predicoes(df_preparado)
"""

import logging
import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from config.settings import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# CACHE DE MODELOS
#
# Funciona como o singleton do settings: carrega uma vez, reutiliza depois.
# A chave do cache é o caminho resolvido (absoluto) do arquivo.
#
# Na Fase 5 (Continuous Training), quando o Model Registry existir,
# este cache evolui pra consultar o registry. A interface externa
# (carregar_modelo) não muda.
# ---------------------------------------------------------------------------
_modelo_cache: dict[str, object] = {}


def carregar_modelo(caminho: Path) -> object:
    """
    Carrega um modelo .joblib com cache em memória.

    Se o modelo já foi carregado nesta sessão, retorna do cache.
    Se o caminho não existe, estoura FileNotFoundError imediatamente
    """
    caminho_str = str(caminho.resolve())

    if caminho_str in _modelo_cache:
        logger.debug(f"Modelo carregado do cache: {caminho.name}")
        return _modelo_cache[caminho_str]

    if not caminho.exists():
        raise FileNotFoundError(
            f"Modelo não encontrado: {caminho}. "
            f"Verifique se o arquivo existe e se o caminho em settings está correto."
        )

    logger.info(f"Carregando modelo: {caminho.name}")
    modelo = joblib.load(caminho)
    _modelo_cache[caminho_str] = modelo
    return modelo


def limpar_cache() -> None:
    """
    Limpa o cache de modelos.

    Útil em testes (pytest) e no futuro quando o Continuous Training
    promover um challenger a champion — o cache do champion antigo
    precisa ser invalidado.
    """
    _modelo_cache.clear()
    logger.info("Cache de modelos limpo")

# ---------------------------------------------------------------------------
# PREDIÇÃO + CONFIANÇA
# ---------------------------------------------------------------------------

def _predizer_com_confianca(
    modelo: object,
    df: pd.DataFrame,
    features: list[str],
    nome_modelo: str
) -> tuple[np.ndarray, np.ndarray]:
    """
    Faz predição e calcula confiança (max da probabilidade por linha).

    Retorna:
        predicoes: array de classes preditas
        confiancas: array de floats entre 0 e 1 (max predict_proba por linha)

    A confiança é o max(predict_proba) — ou seja, quão "certo" o modelo
    está da classe que escolheu. Valores baixos (~0.3-0.5) indicam que o
    modelo está dividido entre classes e a assistente deve revisar com atenção.

    NOTA SOBRE CALIBRAÇÃO (Fase 6, ADR-0009):
        Hoje, essa confiança NÃO é uma probabilidade calibrada.
        Um valor de 0.8 não significa "80% de chance de estar certo".
        Significa apenas que o modelo está mais confiante aqui do que
        num caso com 0.5. Na Fase 6, calibramos com isotonic regression
        pra que a confiança reflita probabilidade real.
    """
    logger.info(f"Gerando predições com {nome_modelo} ({len(df)} registros)")

    predicoes = modelo.predict(df[features])
    probabilidades = modelo.predict_proba(df[features])
    confiancas = np.max(probabilidades, axis=1)

    logger.info(
        f"{nome_modelo}: confiança média={confiancas.mean():.3f}, "
        f"mínima={confiancas.min():.3f}, máxima={confiancas.max():.3f}"
    )

    return predicoes, confiancas

# ---------------------------------------------------------------------------
# BUSINESS RULE OVERRIDE
# ---------------------------------------------------------------------------

def _aplicar_override_cirurgia(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """
    Corrige predições onde o modelo disse "Clínico" mas o paciente fez cirurgia.

    Regra: se a coluna 'cirurgia' contém um valor real (não está na lista
    de valores_nao_cirurgicos), e o modelo predisse a classe de origem
    (ex: "Procedimentos clínicos"), corrige para a classe de destino
    (ex: "Procedimentos cirúrgicos").

    Retorna:
        df: DataFrame com correções aplicadas
        qtd_corrigidos: quantidade de registros corrigidos (pra log e métricas)
    """
    valores_nao_cirurgicos = settings.valores_nao_cirurgicos
    classe_origem = settings.override_classe_origem
    classe_destino = settings.override_classe_destino

    condicao_cirurgia = ~df["cirurgia"].astype(str).isin(valores_nao_cirurgicos)
    condicao_erro = df["PREVISAO_GRUPO"] == classe_origem
    indices_corrigir = df[condicao_cirurgia & condicao_erro].index

    qtd_corrigidos = len(indices_corrigir)

    if qtd_corrigidos > 0:
        logger.warning(
            f"Override: corrigindo {qtd_corrigidos} predições "
            f"de '{classe_origem}' para '{classe_destino}'"
        )
        df.loc[indices_corrigir, "PREVISAO_GRUPO"] = classe_destino
    else:
        logger.info("Override: nenhuma correção necessária")

    return df, qtd_corrigidos

# ---------------------------------------------------------------------------
# FUNÇÃO PRINCIPAL — ORQUESTRA TUDO
# ---------------------------------------------------------------------------

def gerar_predicoes(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    Gera predições de GRUPO_SUS e COMPLEXIDADE_SUS com confiança e override.

    Parâmetros:
        df: DataFrame já preparado (features engineering aplicada,
            colunas renomeadas, cirurgias merged). Quem prepara é o
            orquestrador (gerar_previsoes.py ou app.py), não este módulo.

    Retorna:
        df: DataFrame original + colunas de predição e confiança
        metadados: dict com métricas do processamento, ex:
            {
                "total_registros": 915,
                "override_corrigidos": 3,
                "confianca_media_grupo": 0.87,
                "confianca_media_complexidade": 0.91,
                "baixa_confianca_grupo": 42,
                "baixa_confianca_complexidade": 28,
            }
    """
    # Carrega modelos (do cache se já carregados)
    modelo_grupo = carregar_modelo(settings.modelo_grupo_path)
    modelo_complexidade = carregar_modelo(settings.modelo_complexidade_path)

    # Predição + confiança: GRUPO_SUS
    pred_grupo, conf_grupo = _predizer_com_confianca(
        modelo_grupo, df, settings.features_grupo, "GRUPO_SUS"
    )
    df["PREVISAO_GRUPO"] = pred_grupo
    df["CONFIANCA_GRUPO"] = conf_grupo

    # Predição + confiança: COMPLEXIDADE_SUS
    pred_complex, conf_complex = _predizer_com_confianca(
        modelo_complexidade, df, settings.features_complexidade, "COMPLEXIDADE_SUS"
    )
    df["PREVISAO_COMPLEXIDADE"] = pred_complex
    df["CONFIANCA_COMPLEXIDADE"] = conf_complex

    # Business Rule Override (só afeta GRUPO)
    df, qtd_override = _aplicar_override_cirurgia(df)

    # Limiar de confiança baixa (abaixo de 0.7, a assistente deve revisar com atenção)
    limiar_confianca = 0.7

    # Metadados para a GUI e para logging
    metadados = {
        "total_registros": len(df),
        "override_corrigidos": qtd_override,
        "confianca_media_grupo": float(conf_grupo.mean()),
        "confianca_media_complexidade": float(conf_complex.mean()),
        "baixa_confianca_grupo": int((conf_grupo < limiar_confianca).sum()),
        "baixa_confianca_complexidade": int((conf_complex < limiar_confianca).sum()),
    }

    logger.info(
        f"Predição concluída: {metadados['total_registros']} registros, "
        f"{metadados['override_corrigidos']} overrides, "
        f"{metadados['baixa_confianca_grupo']} com baixa confiança (grupo)"
    )

    return df, metadados