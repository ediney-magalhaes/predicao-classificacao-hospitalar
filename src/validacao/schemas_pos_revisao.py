"""
Validação Pós-Revisão — Schema Pandera para escrita na Bronze.

RESPONSABILIDADE:
    Validar a planilha REVISADA pela assistente ANTES de anonimizar
    e enviar para o BigQuery (Bronze). É a última barreira antes
    do dado virar registro permanente no warehouse.

DIFERENÇA DO validacao.py:
    - validacao.py valida ENTRADA (planilhas brutas pra gerar predição)
    - schemas_ingestao.py valida SAÍDA REVISADA (planilha corrigida
      pela assistente, pronta pra virar Bronze)

    As regras aqui são mais rígidas: a planilha revisada DEVE ter
    as colunas de predição preenchidas com valores do domínio válido.

CAMADA DE VALIDAÇÃO (ADR-0001):
    Mesma camada 2 (Pandera → DataFrames), mas num momento diferente
    do fluxo: pós-revisão, pré-ingestão.
"""

import logging
import pandas as pd
import pandera.pandas as pa
from pandera.pandas import Column, Check, DataFrameSchema

logger = logging.getLogger(__name__)

# DOMÍNIOS VÁLIDOS (extraídos do arquivo de classificação SUS)
# Fonte de verdade: data/Classificação_grupo&complexidade_SUS.xlsx
# Se o SUS adicionar uma classe, atualizar o arquivo — o schema reflete.

def _carregar_dominios() -> tuple[list[str], list[str]]:
    """
    Extrai os valores únicos de GRUPO e COMPLEXIDADE do arquivo
    de classificação oficial.

    Retorna tupla (dominio_grupo, dominio_complexidade).

    Raises:
        FileNotFoundError: se o arquivo não existir no caminho esperado.
            Mensagem explica o que fazer — não deixa o erro genérico subir.
    """
    from config.settings import settings

    caminho = settings.dicionario_classificacao_path

    if not caminho.exists():
        raise FileNotFoundError(
            f"Arquivo de classificação SUS não encontrado em: {caminho}\n"
            f"Este arquivo é obrigatório para validação pós-revisão.\n"
            f"Verifique se ele existe na pasta data/ do projeto."
        )

    df = pd.read_excel(caminho)

    grupo = df["Grupo"].dropna().unique().tolist()
    complexidade = df["Complexidade"].dropna().unique().tolist()

    if not grupo or not complexidade:
        raise ValueError(
            "Arquivo de classificação SUS está vazio ou sem as colunas "
            "esperadas (Grupo, Complexidade)."
        )

    return grupo, complexidade


DOMINIO_GRUPO, DOMINIO_COMPLEXIDADE = _carregar_dominios()

# NORMALIZAÇÃO PRÉ-VALIDAÇÃO
#
# A assistente digita livre no Excel — variações de casing, espaços
# extras e espaços duplos são esperados. Esta função limpa ANTES
# do schema validar, pra não rejeitar por formatação.
#
# A estratégia é: normalizar o digitado e tentar casar com o domínio
# oficial via comparação case-insensitive. Se casar, substitui pelo
# valor canônico. Se não casar, deixa passar — o schema rejeita
# com mensagem clara.

def normalizar_colunas_revisao(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normaliza valores das colunas de predição para o domínio oficial.

    Operações por coluna:
      1. Strip (remove espaços nas pontas)
      2. Colapsa espaços duplos internos
      3. Tenta casar com valor canônico (case-insensitive)
      4. Se casou, substitui pelo canônico. Se não, mantém o original
         (o schema vai rejeitar e mostrar mensagem útil).

    Args:
        df: DataFrame com colunas PREVISAO_GRUPO e/ou PREVISAO_COMPLEXIDADE.

    Returns:
        DataFrame com valores normalizados (cópia, não altera o original).
    """
    df = df.copy()

    # normaliza nomes de colunas que o schema precisa em maiúsculo
    mapa_colunas = {
        "atendimento": "ATENDIMENTO",
        "previsao_grupo": "PREVISAO_GRUPO",
        "previsao_complexidade": "PREVISAO_COMPLEXIDADE",
    }
    df = df.rename(columns={
        col: mapa_colunas[col.lower()]
        for col in df.columns
        if col.lower() in mapa_colunas
    })

    mapa_colunas = {
        "PREVISAO_GRUPO": DOMINIO_GRUPO,
        "PREVISAO_COMPLEXIDADE": DOMINIO_COMPLEXIDADE,
    }

    for coluna, dominio in mapa_colunas.items():
        if coluna not in df.columns:
            continue

        # monta lookup: valor em minúsculo -> valor canônico
        lookup = {v.lower(): v for v in dominio}

        def _normalizar(valor):
            if pd.isna(valor):
                return valor
            limpo = " ".join(str(valor).strip().split())
            return lookup.get(limpo.lower(), limpo)

        df[coluna] = df[coluna].apply(_normalizar)

    return df

# SCHEMA: PLANILHA REVISADA (pós-correção da assistente)
#
# Valida DEPOIS da normalização. Por isso exige valores exatos do
# domínio — a normalização já fez o trabalho de limpar variações.
#
# Colunas validadas:
#   - ATENDIMENTO: chave de pareamento (precisa existir e ser > 0)
#   - PREVISAO_GRUPO: deve conter valor do domínio oficial
#   - PREVISAO_COMPLEXIDADE: idem
#
# strict=False porque a planilha revisada tem todas as outras colunas
# do resultado original (confiança, CIDs, etc.)

schema_pos_revisao = DataFrameSchema(
    columns={
        "ATENDIMENTO": Column(
            dtype="int64",
            nullable=False,
            checks=Check.greater_than(0),
            description="Chave de pareamento com a predição original",
        ),
        "PREVISAO_GRUPO": Column(
            dtype="object",
            nullable=False,
            checks=Check.isin(DOMINIO_GRUPO),
            description="Grupo SUS revisado pela assistente",
        ),
        "PREVISAO_COMPLEXIDADE": Column(
            dtype="object",
            nullable=False,
            checks=Check.isin(DOMINIO_COMPLEXIDADE),
            description="Complexidade SUS revisada pela assistente",
        ),
    },
    strict=False,
    coerce=True,
    name="PlanilhaRevisada",
    description="Schema da planilha pós-revisão, antes da ingestão na Bronze",
)


def validar_planilha_revisada(df: pd.DataFrame) -> tuple[bool, str]:
    """
    Normaliza e valida a planilha revisada pela assistente.

    Fluxo:
      1. Normaliza valores das colunas de predição (strip, case, domínio)
      2. Valida contra o schema
      3. Retorna (sucesso, mensagem) no mesmo padrão do validacao.py

    Args:
        df: DataFrame com a planilha revisada (antes da normalização).

    Returns:
        Tupla (bool, str):
          - True + mensagem de sucesso se válida
          - False + mensagem descritiva se inválida
    """
    df_normalizado = normalizar_colunas_revisao(df)

    try:
        schema_pos_revisao.validate(df_normalizado, lazy=True)
        logger.info(f"Planilha revisada validada: {len(df_normalizado)} linhas")
        return True, f"Planilha revisada válida ({len(df_normalizado)} registros)"
    except pa.errors.SchemaErrors as e:
        erros = e.failure_cases
        msg = _formatar_erros_revisao(erros)
        logger.warning(f"Validação pós-revisão falhou: {len(erros)} erros")
        return False, msg


def _formatar_erros_revisao(failure_cases) -> str:
    """
    Formata erros em mensagem legível para a assistente.

    Diferente do _formatar_erros do validacao.py, aqui inclui os
    valores aceitos quando o erro é de domínio — a assistente precisa
    saber O QUE pode digitar, não só que errou.
    """
    linhas = ["**Problemas encontrados na planilha revisada:**\n"]

    for _, row in failure_cases.iterrows():
        coluna = row.get("column", "geral")
        check = row.get("check", "verificação")
        valor = row.get("failure_case", "")

        if "isin" in str(check):
            if "GRUPO" in str(coluna):
                aceitos = ", ".join(DOMINIO_GRUPO)
            else:
                aceitos = ", ".join(DOMINIO_COMPLEXIDADE)
            linhas.append(
                f'- Coluna **{coluna}**: valor "{valor}" não é válido.\n'
                f"  Valores aceitos: {aceitos}"
            )
        elif "not_nullable" in str(check):
            linhas.append(
                f"- Coluna **{coluna}**: contém células vazias. "
                f"Todas as linhas precisam ter classificação preenchida."
            )
        else:
            linhas.append(f"- Coluna **{coluna}**: {check}")

    linhas.append(
        "\nCorrija os valores indicados e faça o upload novamente."
    )
    return "\n".join(linhas)