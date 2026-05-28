"""
Ingestão histórica na Bronze — execução única.

Lê o CSV consolidado (2012-2024), enriquece com dicionário CID,
anonimiza e envia para Bronze no BigQuery, safra a safra.

Idempotente: a deduplicação por safra no carga_bq garante que
re-executar não duplica dados.

Uso:
    python scripts/ingestao_historica.py
"""

import logging
import sys
from pathlib import Path

import pandas as pd

# adiciona raiz do projeto ao path (script está em scripts/)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import settings
from src.preprocessing.preparo_ml import engenharia_features
from src.ingestion.anonimizacao import anonimizar_dataframe
from src.ingestion.carga_bq import enviar_para_bigquery

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

CSV_PATH = Path("data/historico_saidas(ajustado).csv")
ENCODING = "latin-1"
SEPARADOR = ";"
ANO_LIMITE = 2025  # Exclui 2025 em diante


def main():
    logger.info(f"Lendo {CSV_PATH}...")
    df = pd.read_csv(CSV_PATH, encoding=ENCODING, sep=SEPARADOR)
    logger.info(f"{len(df)} registros lidos")

    # filtra dados antes de 2025
    df = df[df["ANO"] < ANO_LIMITE]
    logger.info(f"{len(df)} registros após filtrar ANO < {ANO_LIMITE}")

    # usa dt_alta para safra_mes
    df["dt_alta"] = pd.to_datetime(df["dt_alta"], dayfirst=True, errors="coerce")
    df["_safra_mes"] = df["dt_alta"].dt.strftime("%Y-%m")

    # remove linhas sem data de alta válida
    sem_data = df["_safra_mes"].isna().sum()
    if sem_data > 0:
        logger.warning(f"{sem_data} registros sem dt_alta válida — serão ignorados")
        df = df.dropna(subset=["_safra_mes"])

    # enriquecimento CID (merge com dicionário)
    logger.info("Enriquecendo com dicionário CID...")
    df = engenharia_features(df)
    
    # força colunas numéricas que têm mixed types no CSV histórico
    colunas_int = ["registro_ans", "entrada_uti", "dt_saida", "prontuario", "atendimento"]
    for col in colunas_int:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # agrupa por safra e envia
    safras = sorted(df["_safra_mes"].unique())
    logger.info(f"{len(safras)} safras a processar: {safras[0]} a {safras[-1]}")

    total_enviado = 0
    erros = []

    for safra in safras:
        df_safra = df[df["_safra_mes"] == safra].copy()
        df_safra = df_safra.drop(columns=["_safra_mes"])

        try:
            df_anon = anonimizar_dataframe(df_safra)
            qtd = enviar_para_bigquery(df_anon, safra)
            total_enviado += qtd
            logger.info(f"  {safra}: {qtd} registros enviados")
        except Exception as e:
            logger.exception(f"  {safra}: ERRO - {e}")
            erros.append(safra)

    logger.info(f"\nIngestão concluída: {total_enviado} registros em {len(safras)} safras")
    if erros:
        logger.error(f"Safras com erro: {erros}")


if __name__ == "__main__":
    main()