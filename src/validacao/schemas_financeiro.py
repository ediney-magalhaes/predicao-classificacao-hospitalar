import logging
import pandas as pd
import pandera.pandas as pa
from pandera.pandas import Column, Check, DataFrameSchema

logger = logging.getLogger(__name__)

schema_financeiro = DataFrameSchema(
    columns={
        "NR_ATENDIMENTO": Column(
            dtype="int64",
            nullable=False,
            checks=Check.greater_than(0),
            description="Chave de pareamento com ATENDIMENTO da Bronze principal",
        ),
        "NR_INTERNO_CONTA": Column(
            dtype="int64",
            nullable=False,
            checks=Check.greater_than(0),
            description="Identificação da conta do paciente",
        ),
        "MES_ANO_PRODUCAO": Column(
            dtype="object",
            nullable=False,
            checks=Check.str_matches(r'^[a-z]{3} \d{4}$'),
            description="Identificação do mês de produção do valor da conta do paciente",
        ),
        "ANO_PRODUCAO": Column(
            dtype="int64",
            nullable=False,
            checks=Check.in_range(2020, 2030),
            description="Identificação do ano de produção do valor da conta do paciente",
        ),
        "VALOR": Column(
            dtype="float",
            nullable=False,
            checks=Check.ge(0),
            description="Faturamento da conta do paciente",
        ),
        "CONVENIO": Column(
            dtype="object",
            nullable=False,
            description="Nome do convênio do paciente",
        ),
        "PACIENTE": Column(
            dtype="object",
            nullable=False,
            description="Identificação do paciente",
        ),
        "VALOR RECEBIDO": Column(
            dtype="float",
            nullable=True,
            checks=Check.ge(0),
            description="Valor recebido sobre o faturamento",
        ),
        "VALOR GLOSA": Column(
            dtype="float",
            nullable=True,
            checks=Check.ge(0),
            description="Valor não recebido sobre o faturamento",
        ),
    },
    strict=False,
    coerce=True,
    name="RelatorioContas",
    description="Schema do relatório de análise das contas, antes da anonimização e ingestão na Bronze",
)

def validar_contas(df: pd.DataFrame) -> tuple[bool, str]:
    """
        Valida o relatório de análise das contas hospitalares.

        Args:
            df: DataFrame bruto do relatório de análise das contas (antes da
                anonimização).

        Returns:
            Tupla (bool, str):
                - True + mensagem de sucesso se válido
                - False + mensagem descritiva se inválido
    """
    try:
        schema_financeiro.validate(df, lazy=True)
        logger.info(f"Relatório de Análise das Contas validado: {len(df)} linhas")
        return True, f"Relatório de Análise das Contas validado {len(df)} registros"
    except pa.errors.SchemaErrors as e:
        erros = e.failure_cases
        msg = _formatar_erros_contas(erros)
        logger.warning(f"Validação das contas falhou: {len(erros)} erros")
        return False, msg

def _formatar_erros_contas(failure_cases) -> str:
    """
        Formata erros de validação em mensagem legível.
    """
    # lista de strings que, no final, vira o texto completo da mensagem.
    linhas = ["**Problemas encontrados no relatório de análise das contas:**\n"]

    # failure_cases é o DataFrame que o Pandera devolve dentro da exceção iterrows() percorre esse DataFrame linha por linha.
    # "_" no lugar do índice é pra dizer "esse valor existe, mas não preciso dele aqui" usa o conteúdo de cada linha (row).
    for _, row in failure_cases.iterrows():
        # "column": qual coluna do schema_financeiro teve o problema
        coluna = row.get("column", "geral")
        # "check": qual verificação falhou (ex: "greater_than(0)",
        check = row.get("check", "verificação")
        # valor real que disparou o problema.
        valor = row.get("failure_case", "")
        linhas.append(f"A coluna {coluna} falhou na verificação {check} com o valor {valor}!")
    linhas.append("Corrija os erros nos valores exportados do relatório e inicie a validação novamente!")
    return "\n".join(linhas)

        