"""
Validação de Dados de Entrada — Relatório de Movimentações (Pandera Schema).

RESPONSABILIDADE:
    Validar o relatório de movimentações internas do hospital antes da
    anonimização e ingestão na Bronze (bronze_movimentacoes_anonimizado).

    Este relatório é uma 4ª fonte de dados, distinta das 3 planilhas de
    entrada usadas para gerar predições (Saídas/Epidemio, Altas/MV,
    Cirurgias). Ele não alimenta o modelo, é usado para reconstruir,
    via dbt (Silver), a passagem de cada atendimento por UTI.

CAMADA DE VALIDAÇÃO (ADR-0001):
    Camada 2 (Pandera → DataFrames), no momento de ingestão desta
    4ª fonte — mesmo papel que validacao.py cumpre para as 3 planilhas
    originais.
"""

import logging
import pandas as pd
import pandera.pandas as pa
from pandera.pandas import Column, Check, DataFrameSchema

logger = logging.getLogger(__name__)

# DOMÍNIO: TIPO DE MOVIMENTAÇÃO
# Valores fechados, confirmados contra amostra real do relatório.
# Qualquer valor fora dessa lista indica mudança no relatório de origem

DOMINIO_TIPO_MOVIMENTACAO = [
    "INTERNACAO",
    "TRANSFER. DE",
    "TRANSFER. PARA",
    "ALTA",
]

# SCHEMA: RELATÓRIO DE MOVIMENTAÇÕES (entrada bruta, pré-anonimização)
#
# Colunas validadas:
#   - ATEND: chave de pareamento com a Bronze principal (precisa existir
#     e ser > 0)
#   - TIPO: deve conter um dos 4 valores do domínio fechado
#   - ORIGEM/DESTINO: nullable — INTERNACAO não tem origem,
#     ALTA não tem destino (confirmado na amostra real)
#   - DATA/HORA: strings — parsing e combinação ficam para a Silver (dbt)
#
# strict=False para não travar a ingestão se o relatório ganhar uma coluna nova

schema_movimentacoes = DataFrameSchema(
    columns={
        "ATEND": Column(
            dtype="int64",
            nullable=False,
            checks=Check.greater_than(0),
            description="Chave de pareamento com ATENDIMENTO da Bronze principal",
        ),
        "TIPO": Column(
            dtype="object",
            nullable=False,
            checks=Check.isin(DOMINIO_TIPO_MOVIMENTACAO),
            description="Tipo de evento de movimentação",
        ),
        "ORIGEM": Column(
            dtype="object",
            nullable=True,
            description="Setor/leito de origem (vazio em INTERNACAO)",
        ),
        "DESTINO": Column(
            dtype="object",
            nullable=True,
            description="Setor/leito de destino (vazio em ALTA)",
        ),
        "UNIDADE": Column(
            dtype="object",
            nullable=False,
            description="Unidade da movimentação — base para identificar passagem por UTI",
        ),
        "DATA": Column(
            dtype="object",
            nullable=False,
            description="Data do evento, formato bruto (parse na Silver)",
        ),
        "HORA": Column(
            dtype="object",
            nullable=False,
            description="Hora do evento, formato bruto (parse na Silver)",
        ),
    },
    strict=False,
    coerce=True,
    name="RelatorioMovimentacoes",
    description="Schema do relatório de movimentações, antes da anonimização e ingestão na Bronze",
)

def validar_movimentacoes(df: pd.DataFrame) -> tuple[bool, str]:
    """
    Valida o relatório de movimentações contra o schema definido.

    Args:
        df: DataFrame bruto do relatório de movimentações (antes da
            anonimização).

    Returns:
        Tupla (bool, str):
          - True + mensagem de sucesso se válido
          - False + mensagem descritiva se inválido
    """
    try:
        schema_movimentacoes.validate(df, lazy=True)
        logger.info(f"Relatório de movimentações validado: {len(df)} linhas")
        return True, f"Relatório de movimentações válido ({len(df)} registros)"
    except pa.errors.SchemaErrors as e:
        erros = e.failure_cases
        msg = _formatar_erros_movimentacoes(erros)
        logger.warning(f"Validação de movimentações falhou: {len(erros)} erros")
        return False, msg


def _formatar_erros_movimentacoes(failure_cases) -> str:
    """
    Formata erros de validação em mensagem legível.

    Segue o mesmo padrão de _formatar_erros_revisao — mostra os
    valores aceitos quando o erro é de domínio (coluna TIPO).
    """
    linhas = ["**Problemas encontrados no relatório de movimentações:**\n"]

    for _, row in failure_cases.iterrows():
        coluna = row.get("column", "geral")
        check = row.get("check", "verificação")
        valor = row.get("failure_case", "")

        if "isin" in str(check) and coluna == "TIPO":
            aceitos = ", ".join(DOMINIO_TIPO_MOVIMENTACAO)
            linhas.append(
                f'- Coluna **{coluna}**: valor "{valor}" não é válido.\n'
                f"  Valores aceitos: {aceitos}"
            )
        elif "not_nullable" in str(check):
            linhas.append(
                f"- Coluna **{coluna}**: contém células vazias, mas essa "
                f"coluna é obrigatória."
            )
        else:
            linhas.append(f"- Coluna **{coluna}**: {check}")

    linhas.append("\nVerifique o arquivo de origem e tente novamente.")
    return "\n".join(linhas)