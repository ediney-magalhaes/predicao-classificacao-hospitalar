"""
Orquestrador de Predições — Sistema de Classificação SUS.

RESPONSABILIDADES:
    Recebe os 3 DataFrames de entrada (saídas, altas MV, cirurgias),
    executa toda a pipeline de preparação e predição, e devolve o
    resultado final + metadados.

    Este módulo NÃO faz I/O (não lê Excel, não salva arquivo).
    Quem faz I/O é o chamador:
        - Terminal: bloco if __name__ == '__main__' no final deste arquivo
        - GUI: app.py (Streamlit)
        - Futuro: API FastAPI, pipeline automatizado, etc.

FLUXO:
    1. Deduplicação por ATENDIMENTO
    2. Validação cruzada com altas do MV (intrusos, faltantes)
    3. Preparação de colunas (CID, cirurgias, lowercase)
    4. Feature engineering (dicionário CID → Capítulo + Grupo)
    5. Predição + confiança + override (delegado a src.inference.predicao)
    6. Relatório de avaliação (quando gabarito disponível)
"""

import logging
import pandas as pd
from sklearn.metrics import classification_report

from config.settings import settings
from src.preprocessing.preparo_ml import engenharia_features
from src.inference.predicao import gerar_predicoes

logger = logging.getLogger(__name__)


def processar_previsoes(
    df_saidas: pd.DataFrame,
    df_altas_mv: pd.DataFrame,
    df_cirurgias: pd.DataFrame,
) -> tuple[pd.DataFrame, dict]:
    """
    Pipeline completa de preparação e predição.

    Parâmetros:
        df_saidas: planilha de saídas do mês (Epidemio)
        df_altas_mv: planilha de altas extraída do sistema MV
        df_cirurgias: planilha de cirurgias realizadas

    Retorna:
        df_resultado: DataFrame com todas as colunas originais + predições + confiança
        metadados: dict com métricas do processamento (alertas, contagens, avaliação)
    """
    metadados = {"alertas": [], "stats": {}}

    # ------------------------------------------------------------------
    # 1. DEDUPLICAÇÃO
    # ------------------------------------------------------------------
    total_bruto = len(df_saidas)
    df_saidas = df_saidas.drop_duplicates(subset=["ATENDIMENTO"])
    total_dedup = len(df_saidas)

    logger.info(f"Base bruta: {total_bruto} linhas -> após deduplicação: {total_dedup}")
    metadados["stats"]["total_bruto"] = total_bruto
    metadados["stats"]["total_deduplicado"] = total_dedup

    if total_bruto != total_dedup:
        qtd_removidos = total_bruto - total_dedup
        metadados["alertas"].append(
            f"{qtd_removidos} registros duplicados removidos por ATENDIMENTO"
        )

    # ------------------------------------------------------------------
    # 2. VALIDAÇÃO CRUZADA COM ALTAS DO MV
    # ------------------------------------------------------------------
    atend_planilha = set(df_saidas["ATENDIMENTO"])
    atend_mv = set(
        pd.to_numeric(df_altas_mv.iloc[:, 1], errors="coerce").dropna()
    )

    faltantes = atend_mv - atend_planilha
    intrusos = atend_planilha - atend_mv

    # Filtra: só mantém quem está no MV
    df_saidas = df_saidas[df_saidas["ATENDIMENTO"].isin(atend_mv)]
    
    if faltantes:
        logger.warning(f"Faltam {len(faltantes)} atendimentos do MV na planilha")
        metadados["alertas"].append(
            f"ATENÇÃO: {len(faltantes)} atendimentos do MV não constam na planilha de saídas"
        )
    else:
        logger.info("Validação MV: todos os atendimentos presentes")

    if intrusos:
        logger.warning(f"{len(intrusos)} atendimentos de outro hospital removidos")
        metadados["alertas"].append(
            f"{len(intrusos)} atendimentos de outro hospital foram removidos"
        )

    metadados["stats"]["faltantes_mv"] = len(faltantes)
    metadados["stats"]["lista_faltantes_mv"] = sorted(faltantes)
    metadados["stats"]["intrusos_removidos"] = len(intrusos)
    metadados["stats"]["total_apos_validacao"] = len(df_saidas)

    # ------------------------------------------------------------------
    # 3. PREPARAÇÃO DE COLUNAS
    # ------------------------------------------------------------------
    # Remove COD_CID_SUMARIO (não usada no modelo)
    if "COD_CID_SUMARIO" in df_saidas.columns:
        df_saidas = df_saidas.drop(columns=["COD_CID_SUMARIO"])

    # Preenche CID_1_PRINCIPAL com CID_ENTRADA quando nulo
    df_saidas["CID_1_PRINCIPAL"] = df_saidas["CID_1_PRINCIPAL"].fillna(
        df_saidas["CID_ENTRADA"]
    )

    # ------------------------------------------------------------------
    # 4. MERGE COM CIRURGIAS
    # ------------------------------------------------------------------
    df_cirurgias = df_cirurgias[df_cirurgias["SN_PRINCIPAL"] == "SIM"]
    df_cirurgias = df_cirurgias.drop_duplicates(subset=["ATENDIMENTO"])
    logger.info(f"Cirurgias principais (deduplicadas): {len(df_cirurgias)}")

    df_saidas = pd.merge(
        df_saidas,
        df_cirurgias[["ATENDIMENTO", "DESCRICAO_CIRURGIA"]],
        on="ATENDIMENTO",
        how="left",
    )

    # ------------------------------------------------------------------
    # 5. NORMALIZAÇÃO + FEATURE ENGINEERING
    # ------------------------------------------------------------------
    # Lowercase nas colunas (ANTES do merge com dicionário CID,
    # porque o dicionário adiciona colunas com nomes em maiúsculo
    # que o modelo espera)
    df_saidas.columns = df_saidas.columns.str.lower()

    # Enriquecimento semântico com dicionário de CIDs
    df_saidas = engenharia_features(df_saidas)

    # Renomeia e preenche cirurgias
    df_saidas = df_saidas.rename(columns={"descricao_cirurgia": "cirurgia"})
    df_saidas["cirurgia"] = df_saidas["cirurgia"].fillna("DESCONHECIDO")

    # ------------------------------------------------------------------
    # 6. PREDIÇÃO (delegada ao módulo de inferência)
    # ------------------------------------------------------------------
    df_saidas, metadados_predicao = gerar_predicoes(df_saidas)
    metadados["stats"].update(metadados_predicao)

    # ------------------------------------------------------------------
    # 7. AVALIAÇÃO (quando gabarito existe)
    # ------------------------------------------------------------------
    if "grupo_sus" in df_saidas.columns and "complexidade_sus" in df_saidas.columns:
        logger.info("Gabarito encontrado — gerando relatório de avaliação")

        report_grupo = classification_report(
            df_saidas["grupo_sus"],
            df_saidas["PREVISAO_GRUPO"],
            zero_division=0,
            output_dict=True,
        )
        report_complexidade = classification_report(
            df_saidas["complexidade_sus"],
            df_saidas["PREVISAO_COMPLEXIDADE"],
            zero_division=0,
            output_dict=True,
        )

        metadados["avaliacao"] = {
            "grupo_sus": report_grupo,
            "complexidade_sus": report_complexidade,
        }

        logger.info(
            f"Acurácia GRUPO: {report_grupo['accuracy']:.4f} | "
            f"Acurácia COMPLEXIDADE: {report_complexidade['accuracy']:.4f}"
        )
    else:
        logger.info(
            "Colunas de gabarito (grupo_sus, complexidade_sus) não encontradas. "
            "Relatório de avaliação não gerado."
        )
        metadados["stats"]["distribuicao_grupo"] = (
            df_saidas["PREVISAO_GRUPO"].value_counts().to_dict()
        )
        metadados["stats"]["distribuicao_complexidade"] = (
            df_saidas["PREVISAO_COMPLEXIDADE"].value_counts().to_dict()
        )

    return df_saidas, metadados


# ======================================================================
# ADAPTER DE TERMINAL
#
# Este bloco é o "adapter" que faz I/O para uso via linha de comando.
# Lê os 3 Excel, chama processar_previsoes (que não sabe de Excel),
# e salva o resultado.
#
# A GUI (app.py) será outro adapter que faz upload via Streamlit,
# chama a mesma função, e exibe na tela.
# ======================================================================
if __name__ == "__main__":
    import sys

    # Configura logging para o terminal
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
        datefmt="%H:%M:%S",
    )

    # --- CONFIGURAÇÃO DA EXECUÇÃO ---
    # Altere estes valores para o mês que deseja processar
    arquivo_altas = "ALTAS.xlsx"
    arquivo_cirurgias = "Cirurgias Realizadas 03-2026.xlsx"
    arquivo_saidas = "EPIDEMIO 03 2026.xlsx"
    arquivo_output = "Banco Epidemio - Marco 2026.xlsx"

    # --- LEITURA (I/O) ---
    logger.info("Lendo planilhas de entrada...")
    df_saidas = pd.read_excel(arquivo_saidas)
    df_altas = pd.read_excel(arquivo_altas)
    df_cirurgias = pd.read_excel(arquivo_cirurgias)

    # --- PROCESSAMENTO (lógica pura) ---
    df_resultado, metadados = processar_previsoes(df_saidas, df_altas, df_cirurgias)

    # --- ESCRITA (I/O) ---
    df_resultado.to_excel(arquivo_output, index=False)
    logger.info(f"Resultado salvo em: {arquivo_output}")

    # --- RESUMO ---
    if metadados.get("alertas"):
        print("\n⚠ ALERTAS:")
        for alerta in metadados["alertas"]:
            print(f"  • {alerta}")

    stats = metadados["stats"]
    print(f"\nRegistros processados: {stats.get('total_apos_validacao', '?')}")
    print(f"Overrides aplicados: {stats.get('override_corrigidos', 0)}")
    print(
        f"Baixa confiança (grupo): {stats.get('baixa_confianca_grupo', '?')} | "
        f"(complexidade): {stats.get('baixa_confianca_complexidade', '?')}"
    )

    # Relatório de performance (se existir)
    try:
        with open("relatorio_performance.txt", "r") as f:
            print(f"\n{f.read()}")
    except FileNotFoundError:
        pass