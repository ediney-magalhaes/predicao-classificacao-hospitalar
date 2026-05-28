"""
Registro de auditoria do ciclo HITL.

Monta o evento de auditoria com metadados (quem revisou, quando,
hash dos arquivos, métricas de correção) e persiste no BigQuery
na tabela audit.hitl_events.

Esse registro é a fonte de verdade para:
  - Rastreabilidade (LGPD: quem alterou o quê, quando)
  - Dashboard de performance do modelo ao longo do tempo
  - Decisão de retreino (taxa de correção subindo = modelo degradando)
"""

import hashlib
from datetime import datetime, timezone

import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account

from config.settings import settings


def _hash_dataframe(df: pd.DataFrame) -> str:
    """
    Gera hash SHA-256 do conteúdo de um DataFrame.

    Serve como fingerprint do arquivo: se a assistente alterar
    qualquer célula, o hash muda. Isso garante que o registro
    de auditoria identifica qual versão do arquivo foi processada.

    Não confundir com o hash de anonimização (que protege dados
    pessoais). Este hash protege a integridade do processo.

    Args:
        df: DataFrame cujo conteúdo será hasheado.

    Returns:
        String hexadecimal SHA-256 do conteúdo serializado.
    """
    conteudo = pd.util.hash_pandas_object(df).values.tobytes()
    return hashlib.sha256(conteudo).hexdigest()


def registrar_evento_hitl(
    df_original: pd.DataFrame,
    df_revisado: pd.DataFrame,
    metricas: dict,
    safra_mes: str,
    revisor: str = "assistente_epidemio",
    tempo_revisao_min: int | None = None,
) -> dict:
    """
    Monta e envia registro de auditoria para o BigQuery.

    Args:
        df_original: DataFrame com predições do modelo (antes da revisão).
        df_revisado: DataFrame após revisão humana.
        metricas: Dicionário retornado por calcular_diferencas().
        safra_mes: Mês de referência no formato 'YYYY-MM'.
        revisor: Identificador de quem revisou (sem dados pessoais).
        tempo_revisao_min: Tempo estimado de revisão em minutos.

    Returns:
        Dicionário com o evento registrado (útil pra GUI exibir resumo).
    """
    evento = {
        "safra_mes": safra_mes,
        "data_revisao": datetime.now(timezone.utc).isoformat(),
        "revisor": revisor,
        "hash_original": _hash_dataframe(df_original),
        "hash_revisado": _hash_dataframe(df_revisado),
        "total_registros": metricas["total_registros"],
        "correcoes_grupo": metricas.get("correcoes_grupo", 0),
        "correcoes_complexidade": metricas.get("correcoes_complexidade", 0),
        "correcoes_ambos": metricas.get("correcoes_ambos", 0),
        "taxa_correcao_grupo": metricas.get("taxa_correcao_grupo", 0.0),
        "taxa_correcao_complexidade": metricas.get("taxa_correcao_complexidade", 0.0),
        "tempo_revisao_min": tempo_revisao_min,
        "versao_modelo": settings.modelo_versao,
    }

    # persiste no BigQuery
    credenciais = service_account.Credentials.from_service_account_file(
        settings.google_application_credentials
    )
    cliente_bq = bigquery.Client(
        credentials=credenciais,
        project=settings.gcp_project_id,
    )

    tabela = settings.bq_tabela_auditoria
    erros = cliente_bq.insert_rows_json(tabela, [evento])

    if erros:
        raise RuntimeError(
            f"Erro ao inserir evento de auditoria no BigQuery: {erros}"
        )

    return evento