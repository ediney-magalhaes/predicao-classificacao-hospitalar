"""
Configurações centralizadas do projeto — Pydantic BaseSettings.

POR QUE ESTE ARQUIVO EXISTE:
    Antes, caminhos de modelos, listas de features e valores de override
    estavam espalhados como strings hardcoded dentro de gerar_previsoes.py.
    Se algo mudasse, era preciso caçar em vários lugares.

    Agora, TUDO que é configurável vive aqui. O resto do código importa
    `settings` e usa `settings.modelo_grupo_path`, `settings.features_grupo`, etc.

COMO FUNCIONA:
    1. Pydantic BaseSettings lê variáveis de ambiente (e do .env) automaticamente.
    2. Se a variável não está no ambiente, usa o valor default definido aqui.
    3. Se o valor não passa na validação de tipo, estoura erro ANTES do código rodar.

    Isso significa que um caminho de modelo errado, uma lista de features vazia,
    ou um salt faltando são pegos na inicialização — não no meio de uma predição.

REFERÊNCIA:
    https://docs.pydantic.dev/latest/concepts/pydantic_settings/
"""

from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field

# Diretório raiz do projeto
# config/settings.py > sobe 1 nível > raiz do projeto
PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """
    Configurações do Sistema Preditivo de Classificação SUS.

    Divididas em seções lógicas. Cada atributo é uma config que pode ser
    sobrescrita por variável de ambiente ou pelo .env.

    Exemplo: se no .env existir SALT_SUS=abc123, o valor de self.salt_sus
    será 'abc123' automaticamente, sem precisar de os.getenv().
    """

    # SEGURANÇA E GCP
    # Estas vêm do .env — sem defaults, porque são obrigatórias.
    # Se faltar, Pydantic estoura ValidationError na inicialização.
    salt_sus: str = Field(
        ...,  # ... = obrigatório, sem default
        description="Salt criptográfico para anonimização SHA-256"
    )
    google_application_credentials: str = Field(
        ...,
        description="Caminho para o arquivo de credenciais GCP"
    )
    gcp_project_id: str = Field(
        ...,
        description="ID do projeto no Google Cloud Platform"
    )

    # CAMINHOS DOS MODELOS
    # Defaults apontam para a raiz do projeto. Se amanhã os modelos forem
    # para uma pasta models/, basta mudar aqui — o resto do código nem percebe.
    modelo_grupo_path: Path = Field(
        default=PROJECT_ROOT / "modelo_grupo_sus.joblib",
        description="Caminho do modelo LightGBM para GRUPO_SUS"
    )
    modelo_complexidade_path: Path = Field(
        default=PROJECT_ROOT / "modelo_complexidade_sus.joblib",
        description="Caminho do modelo LightGBM para COMPLEXIDADE_SUS"
    )

    # CAMINHOS DE DADOS DE REFERÊNCIA
    dicionario_cid_path: Path = Field(
        default=PROJECT_ROOT / "data" / "Categorias de CIDs.xlsx",
        description="Caminho do dicionário oficial de CIDs"
    )
    dicionario_classificacao_path: Path = Field(
        default=PROJECT_ROOT / "data" / "Classificação_grupo&complexidade_SUS.xlsx",
        description="Caminho do dicionário oficial de classificação dos grupos e complexidade SUS"
    )

    # FEATURES DOS MODELOS
    # A ordem importa — o LightGBM espera as colunas na mesma ordem do treino.
    # Se adicionar uma feature no treino, adicionar aqui também. 
    features_grupo: list[str] = Field(
        default=[
            "idade", "nr_dias", "cid_entrada",
            "procedimento_entrada", "CAPÍTULO BREVE", "GRUPO",
            "cirurgia", "cid_1_principal", "sexo", "medico_resp_atend"
        ],
        description="Features usadas pelo modelo de GRUPO_SUS (na ordem do treino)"
    )
    features_complexidade: list[str] = Field(
        default=[
            "idade", "nr_dias", "cid_entrada",
            "procedimento_entrada", "cid_1_principal", "cirurgia",
            "CAPÍTULO BREVE", "GRUPO", "sexo", "medico_resp_atend"
        ],
        description="Features usadas pelo modelo de COMPLEXIDADE_SUS (na ordem do treino)"
    )

    # REGRAS DE NEGÓCIO (Business Rule Override)
    # O override corrige predições onde a IA disse "Clínico" mas o paciente
    # fez cirurgia. Estes valores definem o que conta como "sem cirurgia".
    valores_nao_cirurgicos: list[str] = Field(
        default=["DESCONHECIDO", "NAO_CIRURGICO", "nan", "", "-"],
        description="Valores que indicam ausência de cirurgia na coluna 'cirurgia'"
    )
    override_classe_origem: str = Field(
        default="Procedimentos clínicos",
        description="Classe que o override corrige (quando IA erra)"
    )
    override_classe_destino: str = Field(
        default="Procedimentos cirúrgicos",
        description="Classe para a qual o override redireciona"
    )

    # COLUNAS ESPERADAS NAS PLANILHAS DE ENTRADA
    # Usadas pela validação Pandera (Fase 1) para rejeitar uploads inválidos.
    # Se o hospital mudar o nome de uma coluna no sistema, atualizar aqui.
    colunas_obrigatorias_saidas: list[str] = Field(
        default=[
            "ATENDIMENTO", "CID_ENTRADA", "CID_1_PRINCIPAL",
            "COD_CID_SUMARIO", "PROCEDIMENTO_ENTRADA",
            "IDADE", "NR_DIAS", "SEXO", "MEDICO_RESP_ATEND"
        ],
        description="Colunas obrigatórias na planilha de saídas (Epidemio)"
    )
    colunas_obrigatorias_altas: list[str] = Field(
        default=["ATENDIMENTO"],
        description="Colunas obrigatórias na planilha de altas do MV"
    )
    colunas_obrigatorias_cirurgias: list[str] = Field(
        default=["ATENDIMENTO", "SN_PRINCIPAL", "DESCRICAO_CIRURGIA"],
        description="Colunas obrigatórias na planilha de cirurgias"
    )

    # GUI (Streamlit)
    app_titulo: str = Field(
        default="Sistema Preditivo de Classificação SUS",
        description="Título exibido na interface Streamlit"
    )
    app_porta: int = Field(
        default=8501,
        description="Porta onde o Streamlit roda na rede local"
    )

    # STORAGE (Pasta de Rede)
    # Caminho base onde ficam as planilhas revisadas por safra mensal.
    # A W: é o storage primário (ADR-0003). O app salva predições originais
    # e lê de volta pra comparar com a versão revisada.
    # Cria um atributo do tipo Path para Pydantic validar e converter corretamente
    storage_base_path: Path = Field(
        default=Path(r"W:\NOVA PASTA QUALIDADE\Qualidade\Banco de dados\Epidemio"),
        description="Caminho base da pasta de rede onde ficam as planilhas"
    )

    # BIGQUERY (Tabelas e Dataset)
    # Nomes das tabelas que o pipeline de ingestão usa.
    # O dataset 'audit' precisa ser criado manualmente uma vez no BigQuery.
    # Cria um atributo do tipo string para configuração do idenficador no BigQuery
    bq_tabela_bronze: str = Field(
        default="dados_saidas_hospitalares.bronze_saidas_anonimizado",
        description="Tabela bronze no BigQuery (dataset.tabela)"
    )
    bq_tabela_auditoria: str = Field(
        default="audit.hitl_events",
        description="Tabela de auditoria HITL no BigQuery (dataset.tabela)"
    )

    # ANONIMIZAÇÃO (LGPD)
    # Colunas que contêm dados sensíveis. Separadas em dois grupos:
    # - hash: o valor é substituído por SHA-256 (preserva o vínculo entre
    #   registros sem expor o dado real)
    # - drop: a coluna é removida completamente (dado sem valor analítico)
    colunas_hash: list[str] = Field(
        default=["nome_paciente","nm_med_presc", "medico_sumario_alta", "medico_resp_atend"],
        description="Colunas que serão substituídas por hash SHA-256 + salt"
    )
    colunas_drop: list[str] = Field(
        default=[
            # Dados pessoais sem valor analítico
            "data_nascimento", "peso_nascer", "nr_cpf",
            "cep", "endereco", "bairro", "telefone",
            # Colunas administrativas/financeiras
            "plano_convenio", "local_procedencia", "tp_atendimento",
            "leito_saida", "crm_prestador", "cod_cid_sumario",
            "liberacao_alta", "vl_conta", "sn_fechada",
            "vl_honorario", "saps3_admissao", "saps3_obito",
            # Procedimentos e cirurgias secundárias
            "dt_proc_1", "cd_cirurgia_1", "cd_cirurgia_2",
            "prestador1", "dt_proc_2", "cod_proc_2",
            "desc_proc_2", "prestador2",
            # Conselho e prescrição
            "hr_pre_med", "ds_codigo_conselho", "cod_conselho",
            # Colunas extras do histórico (planilhas antigas)
            "cid_2", "cid_3", "cid_4", "cid_5", "cid_6", "cid_7", "cid_8",
            "cid_9", "cid_10", "cid_11", "cid_12", "cid_13", "cid_14", "cid_15",
            "procedimento_2", "procedimento_3", "procedimento_4",
            "procedimento_5", "procedimento_6", "procedimento_7",
            "procedimento_8", "procedimento_9", "procedimento_10",
            "correção_idade", "faixa etaria", "dia semana",
            "mês", "ano", "hora",
            "fonte_pagadora", "convênio_padronizado", "nº_pacientes",
            "cid_principal", "fatores_breves", "cod_procedimento",
            "grupo_categoria", "subcategoria cid-10 (4 dígitos)",
            "nº_dias_uti_geral", "nº_dias_uco", "nº_dias_ped",
            "nº_dias_neo", "setor",
        ],
        description="Colunas removidas antes da ingestão (sensíveis ou sem valor analítico)"
    )

    # VERSIONAMENTO
    # Identifica qual versão do modelo gerou cada predição.
    # Atualizar manualmente a cada retreino até o Model Registry (Fase 5)
    # automatizar isso.
    modelo_versao: str = Field(
        default="v6.0.0",
        description="Versão atual dos modelos em produção"
    )
    sufixo_predicao_original: str = Field(
        default=" - PREDICAO",
        description="Sufixo adicionado ao nome do arquivo de predição original na W:"
    )

    # CONFIGURAÇÃO DO PYDANTIC SETTINGS
    # model_config substitui a antiga class Config (Pydantic v2).
    model_config = {
        # Lê o .env da raiz do projeto automaticamente
        "env_file": str(PROJECT_ROOT / ".env"),
        # Nomes de variáveis no .env são case-insensitive
        # SALT_SUS, salt_sus, Salt_Sus > todos funcionam
        "case_sensitive": False,
        # Se aparecer uma variável no .env que não está definida aqui,
        # ignora em vez de estourar erro. Útil pra não quebrar se alguém
        # adicionar variáveis no .env pra outros fins.
        "extra": "ignore",
    }

# INSTÂNCIA SINGLETON
# Importar em qualquer lugar do projeto:
#     from config.settings import settings
#     print(settings.modelo_grupo_path)
#
# A instância é criada UMA vez na importação. Se o .env estiver errado
# ou faltar variável obrigatória, o erro estoura aqui — não no meio
# de uma predição às 3h da manhã.
settings = Settings()