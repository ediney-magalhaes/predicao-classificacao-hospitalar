"""
Anonimização de dados sensíveis — LGPD compliance.

Este módulo aplica duas operações antes da ingestão no BigQuery:
  1. Hash SHA-256 + salt em colunas identificáveis (nome, CPF, médicos)
  2. Remoção completa de colunas sem valor analítico (endereço, telefone)

As listas de colunas vêm do settings.py (Single Source of Truth).
Se uma coluna sensível nova aparecer, adiciona lá — não aqui.
"""

import hashlib
import pandas as pd
from config.settings import settings

def _aplicar_hash(valor: str, salt: str) -> str | None:
    """
    Aplica SHA-256 + salt em um valor individual.

    O underscore no início do nome indica que é função interna do módulo
    — não deve ser chamada diretamente por outros arquivos.
    Quem usa este módulo chama anonimizar_dataframe(), não esta.

    Args:
        valor: texto a ser hasheado (nome, CPF, etc.)
        salt: salt criptográfico do settings

    Returns:
        Hash SHA-256 hexadecimal, ou None se o valor for nulo/vazio.
    """
    if pd.isna(valor) or str(valor).strip() == "":
        return None
    
    texto_com_salt = str(valor) + salt
    return hashlib.sha256(texto_com_salt.encode("utf-8")).hexdigest()

def anonimizar_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Anonimiza um DataFrame aplicando hash e drop conforme settings.

    Operações na ordem:
      1. Hash SHA-256 nas colunas definidas em settings.colunas_hash
         - Cria coluna 'hash_{nome_original}' com o valor hasheado
         - Remove a coluna original
      2. Drop das colunas definidas em settings.colunas_drop
      3. Padroniza nomes de colunas (lowercase, sem caracteres especiais)

    Args:
        df: DataFrame com dados brutos (pode conter colunas sensíveis)

    Returns:
        DataFrame anonimizado, pronto para ingestão no BigQuery.
    """
    # Cria uma cópia do DataFrame recebido (imutabilidade) e chama o salt do settings
    df = df.copy()
    salt = settings.salt_sus

    # Aplica Hash nas colunas sensíveis
    for coluna in settings.colunas_hash:
        if coluna in df.columns:
            df[f"hash{coluna}"] = df[coluna].apply(
                lambda valor: _aplicar_hash(valor, salt)
            )
            df = df.drop(columns=[coluna])

    # Realiza Drop das colunas que não tem valor analítico
    colunas_para_dropar = [c for c in settings.colunas_drop if c in df.columns]
    df = df.drop(columns=colunas_para_dropar)

    # Padroniza os nomes das colunas
    df.columns = (
        df.columns
        .str.lower()
        .str.replace(" ", "-")
        .str.replace(r"[^a-z0-9_]", "", regex=True)
    )
    return df
