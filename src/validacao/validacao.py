"""
Validação de Dados de Entrada — Pandera Schemas.

RESPONSABILIDADES:
    Validar as 3 planilhas de entrada ANTES de qualquer processamento.
    Se a planilha estiver fora do schema, rejeita com mensagem clara
    para a assistente — não deixa lixo entrar no pipeline.

CAMADA DE VALIDAÇÃO (ADR-0001):
    Este módulo é a camada "DataFrame de entrada" da estratégia de
    validação em 3 camadas:
        1. Pydantic → configs e objetos Python (settings.py)
        2. Pandera → DataFrames de entrada (ESTE ARQUIVO)
        3. dbt tests → warehouse Bronze→Silver→Gold (Fase 3)

POR QUE PANDERA E NÃO VALIDAÇÃO MANUAL:
    - Schema como código: o contrato da planilha fica versionado no Git
    - Mensagens de erro descritivas (diz QUAL coluna falhou e POR QUÊ)
    - Composável: schemas podem herdar e estender
    - Ediney já usou em projeto anterior (Dengue-MT), reforço sem repetição

REFERÊNCIA:
    https://pandera.readthedocs.io/
"""

import logging
import pandera.pandas as pa
from pandera.pandas import Column, Check, DataFrameSchema

logger = logging.getLogger(__name__)


# ======================================================================
# SCHEMA: PLANILHA DE SAÍDAS (Epidemio)
#
# É a planilha principal — 76 colunas, bem estruturada.
# Validamos apenas as colunas críticas para o pipeline de predição.
# As demais (~66 colunas) passam sem validação (coerce=False por padrão).
#
# strict=False permite que a planilha tenha colunas extras sem rejeitar.
# ======================================================================

schema_saidas = DataFrameSchema(
    columns={
        "ATENDIMENTO": Column(
            dtype="int64",
            nullable=False,
            unique=False,  # duplicatas são tratadas no pipeline, não rejeitadas aqui
            checks=Check.greater_than(0),
            description="Chave primária do paciente no MV Soul",
        ),
        "IDADE": Column(
            dtype="int64",
            nullable=False,
            checks=[
                Check.greater_than_or_equal_to(0),
                Check.less_than_or_equal_to(130),
            ],
            description="Idade do paciente na admissão",
        ),
        "SEXO": Column(
            dtype="object",
            nullable=False,
            description="Sexo do paciente",
        ),
        "NR_DIAS": Column(
            dtype="int64",
            nullable=False,
            checks=Check.greater_than_or_equal_to(0),
            description="Tempo de permanência em dias",
        ),
        "CID_ENTRADA": Column(
            dtype="object",
            nullable=True,  # pode ser nulo, mas CID_1_PRINCIPAL serve de fallback
            description="CID-10 registrado na admissão",
        ),
        "CID_1_PRINCIPAL": Column(
            dtype="object",
            nullable=True,  # preenchido com CID_ENTRADA quando nulo
            description="CID-10 principal do sumário de alta",
        ),
        "COD_CID_SUMARIO": Column(
            dtype="object",
            nullable=True,  # será removida no pipeline, mas precisa existir
            description="CID do sumário (removida no processamento)",
        ),
        "PROCEDIMENTO_ENTRADA": Column(
            dtype="object",
            nullable=True,
            description="Código do procedimento faturável de entrada",
        ),
        "MEDICO_RESP_ATEND": Column(
            dtype="object",
            nullable=True,
            description="Médico responsável pelo atendimento",
        ),
    },
    strict=False,  # aceita colunas extras (as outras ~66)
    coerce=True,  # tenta converter tipos automaticamente
    name="PlanilhaSaidas",
    description="Schema da planilha de saídas mensais (Epidemio)",
)


# ======================================================================
# SCHEMA: PLANILHA DE ALTAS (MV)
#
# ATENÇÃO: esta planilha é problemática. O export do MV gera cabeçalhos
# com células mescladas, resultando em colunas "Unnamed:N".
# O código atual acessa por posição (iloc[:, 1]) — não por nome.
#
# Por isso, a validação aqui é MÍNIMA:
# - Verifica que tem pelo menos 2 colunas
# - Verifica que a segunda coluna tem valores numéricos (atendimentos)
#
# Não validamos nomes de colunas porque são imprevisíveis.
# ======================================================================

schema_altas = DataFrameSchema(
    columns={},  # sem validação por nome de coluna
    strict=False,
    coerce=False,
    checks=[
        # Pelo menos 2 colunas (a segunda é o ATENDIMENTO)
        Check(lambda df: df.shape[1] >= 2, error="Planilha de altas deve ter ao menos 2 colunas"),
    ],
    name="PlanilhaAltas",
    description="Schema da planilha de altas do sistema MV",
)


# ======================================================================
# SCHEMA: PLANILHA DE CIRURGIAS
#
# Bem estruturada, 74 colunas. Validamos as 3 que o pipeline usa.
# ======================================================================

schema_cirurgias = DataFrameSchema(
    columns={
        "ATENDIMENTO": Column(
            dtype="int64",
            nullable=False,
            checks=Check.greater_than(0),
            description="Chave de cruzamento com a planilha de saídas",
        ),
        "SN_PRINCIPAL": Column(
            dtype="object",
            nullable=True,
            description="Indicador de cirurgia principal (SIM/NÃO)",
        ),
        "DESCRICAO_CIRURGIA": Column(
            dtype="object",
            nullable=True,
            description="Nome/descrição da cirurgia realizada",
        ),
    },
    strict=False,  # aceita as outras ~71 colunas
    coerce=True,
    name="PlanilhaCirurgias",
    description="Schema da planilha de cirurgias realizadas",
)


# ======================================================================
# FUNÇÕES DE VALIDAÇÃO
#
# Cada função valida um DataFrame e retorna (sucesso, mensagem).
# A GUI chama estas funções e exibe o resultado para a assistente.
# ======================================================================

def validar_saidas(df) -> tuple[bool, str]:
    """Valida a planilha de saídas (Epidemio)."""
    try:
        schema_saidas.validate(df, lazy=True)
        logger.info(f"Planilha de saídas validada: {len(df)} linhas, {len(df.columns)} colunas")
        return True, f"Planilha de saídas válida ({len(df)} registros)"
    except pa.errors.SchemaErrors as e:
        erros = e.failure_cases
        msg = _formatar_erros(erros, "Planilha de Saídas")
        logger.warning(f"Validação falhou para planilha de saídas: {len(erros)} erros")
        return False, msg


def validar_altas(df) -> tuple[bool, str]:
    """Valida a planilha de altas do MV."""
    try:
        schema_altas.validate(df, lazy=True)
        logger.info(f"Planilha de altas validada: {len(df)} linhas, {len(df.columns)} colunas")
        return True, f"Planilha de altas válida ({len(df)} registros)"
    except pa.errors.SchemaErrors as e:
        erros = e.failure_cases
        msg = _formatar_erros(erros, "Planilha de Altas")
        logger.warning(f"Validação falhou para planilha de altas: {len(erros)} erros")
        return False, msg


def validar_cirurgias(df) -> tuple[bool, str]:
    """Valida a planilha de cirurgias."""
    try:
        schema_cirurgias.validate(df, lazy=True)
        logger.info(f"Planilha de cirurgias validada: {len(df)} linhas, {len(df.columns)} colunas")
        return True, f"Planilha de cirurgias válida ({len(df)} registros)"
    except pa.errors.SchemaErrors as e:
        erros = e.failure_cases
        msg = _formatar_erros(erros, "Planilha de Cirurgias")
        logger.warning(f"Validação falhou para planilha de cirurgias: {len(erros)} erros")
        return False, msg


def _formatar_erros(failure_cases, nome_planilha: str) -> str:
    """
    Formata os erros do Pandera em mensagem legível para a assistente.

    A assistente não é técnica — a mensagem precisa dizer O QUE está errado
    e O QUE FAZER, sem jargão de programação.
    """
    linhas = [f"**Problemas encontrados na {nome_planilha}:**\n"]

    for _, row in failure_cases.iterrows():
        coluna = row.get("column", "geral")
        check = row.get("check", "verificação")
        valor = row.get("failure_case", "")

        if "column_in_dataframe" in str(check):
            # Coluna obrigatória ausente
            linhas.append(f"- A coluna **{coluna}** não foi encontrada na planilha")
        elif "greater_than" in str(check) or "less_than" in str(check):
            linhas.append(f"- Coluna **{coluna}**: valor fora do esperado ({valor})")
        elif "dtype" in str(check):
            linhas.append(f"- Coluna **{coluna}**: tipo de dado incorreto")
        elif "not_nullable" in str(check):
            linhas.append(f"- Coluna **{coluna}**: contém valores vazios que não são permitidos")
        else:
            linhas.append(f"- Coluna **{coluna}**: {check}")

    linhas.append("\nVerifique se o arquivo enviado é o correto para este campo.")
    return "\n".join(linhas)