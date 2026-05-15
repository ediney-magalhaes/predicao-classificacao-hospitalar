"""
Interface Streamlit — Sistema Preditivo de Classificação SUS.

Este é o "adapter de GUI" — faz I/O visual (uploads, exibição, download)
e delega toda lógica de negócio para gerar_previsoes.processar_previsoes().

COMO RODAR:
    streamlit run app.py

A assistente acessa via navegador: http://<IP-DO-PC>:8501

AUTENTICAÇÃO:
    Senha definida em .streamlit/secrets.toml (não versionado no Git).
"""

import io
import logging
from datetime import datetime

import pandas as pd
import streamlit as st

from config.settings import settings
from src.validacao.validacao import validar_saidas, validar_altas, validar_cirurgias
from gerar_previsoes import processar_previsoes

# ---------------------------------------------------------------------------
# LOGGING
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title=settings.app_titulo,
    page_icon="🏥",
    layout="wide",
)


# ---------------------------------------------------------------------------
# AUTENTICAÇÃO
#
# Senha simples via st.secrets. O arquivo .streamlit/secrets.toml
# contém: senha = "sua_senha_aqui"
#
# Na Fase 8 (industrialização), isso evolui pra autenticação mais robusta.
# ---------------------------------------------------------------------------
def verificar_autenticacao():
    """Tela de login. Retorna True se autenticado."""
    if st.session_state.get("autenticado", False):
        return True

    st.title("🔐 Acesso ao Sistema")
    st.caption("Sistema Preditivo de Classificação SUS")

    senha = st.text_input("Senha de acesso:", type="password")

    if st.button("Entrar"):
        if senha == st.secrets.get("senha", ""):
            st.session_state["autenticado"] = True
            st.rerun()
        else:
            st.error("Senha incorreta.")

    return False


# ---------------------------------------------------------------------------
# ABA 1: GERAR PREDIÇÕES
# ---------------------------------------------------------------------------
def aba_gerar_predicoes():
    """Fluxo principal: upload → validação → predição → download."""

    st.header("📋 Gerar Predições")
    st.markdown(
        "Faça upload das 3 planilhas do mês, valide os dados "
        "e gere as predições de Grupo e Complexidade SUS."
    )

    # --- Seleção do mês de referência ---
    col_mes, col_ano = st.columns(2)
    with col_mes:
        mes = st.selectbox(
            "Mês de referência:",
            options=list(range(1, 13)),
            format_func=lambda m: [
                "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
            ][m - 1],
            index=datetime.now().month - 2 if datetime.now().month > 1 else 11,
        )
    with col_ano:
        ano = st.selectbox(
            "Ano:",
            options=list(range(2025, datetime.now().year + 1)),
            index=min(datetime.now().year - 2025, 1),
        )

    st.divider()

    # --- Upload dos 3 arquivos ---
    st.subheader("1. Upload das planilhas")

    col1, col2, col3 = st.columns(3)

    with col1:
        arquivo_saidas = st.file_uploader(
            "📄 Planilha de Saídas (Epidemio)",
            type=["xlsx"],
            key="upload_saidas",
            help="Arquivo mensal extraído do sistema com os dados de internação",
        )
    with col2:
        arquivo_altas = st.file_uploader(
            "📄 Altas do Sistema MV",
            type=["xlsx"],
            key="upload_altas",
            help="Lista de altas extraída do MV Soul para validação cruzada",
        )
    with col3:
        arquivo_cirurgias = st.file_uploader(
            "📄 Cirurgias Realizadas",
            type=["xlsx"],
            key="upload_cirurgias",
            help="Planilha de cirurgias realizadas no mês",
        )

    # --- Validação ---
    if arquivo_saidas and arquivo_altas and arquivo_cirurgias:
        st.subheader("2. Validação dos dados")

        # Lê os DataFrames
        try:
            df_saidas = pd.read_excel(arquivo_saidas)
            df_altas = pd.read_excel(arquivo_altas)
            df_cirurgias = pd.read_excel(arquivo_cirurgias)
        except Exception as e:
            st.error(f"Erro ao ler os arquivos: {e}")
            return

        # Valida cada planilha
        resultados_validacao = []

        ok_saidas, msg_saidas = validar_saidas(df_saidas)
        ok_altas, msg_altas = validar_altas(df_altas)
        ok_cirurgias, msg_cirurgias = validar_cirurgias(df_cirurgias)

        # Exibe resultado da validação
        for ok, msg, nome in [
            (ok_saidas, msg_saidas, "Saídas"),
            (ok_altas, msg_altas, "Altas MV"),
            (ok_cirurgias, msg_cirurgias, "Cirurgias"),
        ]:
            if ok:
                st.success(f"✅ {msg}")
            else:
                st.error(f"❌ {msg}")

        todas_validas = ok_saidas and ok_altas and ok_cirurgias

        if not todas_validas:
            st.warning(
                "Corrija os problemas acima e faça upload novamente dos "
                "arquivos com erro."
            )
            return

        st.divider()

        # --- Predição ---
        st.subheader("3. Gerar predições")

        if st.button("🚀 Gerar Predições", type="primary", use_container_width=True):
            with st.spinner("Processando predições... Isso pode levar alguns segundos."):
                try:
                    df_resultado, metadados = processar_previsoes(
                        df_saidas, df_altas, df_cirurgias
                    )
                    # Salva no session_state pra sobreviver ao rerun
                    st.session_state["df_resultado"] = df_resultado
                    st.session_state["metadados"] = metadados
                    st.session_state["mes_ref"] = f"{mes:02d}-{ano}"
                    logger.info(f"Predição concluída para {mes:02d}/{ano}")
                except Exception as e:
                    st.error(f"Erro durante o processamento: {e}")
                    logger.exception("Erro no processamento de predições")
                    return

        # --- Resultado ---
        if "df_resultado" in st.session_state:
            _exibir_resultado(
                st.session_state["df_resultado"],
                st.session_state["metadados"],
                st.session_state["mes_ref"],
            )
    else:
        st.info("Faça upload das 3 planilhas acima para continuar.")


def _exibir_resultado(df: pd.DataFrame, metadados: dict, mes_ref: str):
    """Exibe resultado da predição: alertas, métricas, tabela preview e download."""

    st.divider()
    st.subheader("4. Resultado")

    # --- Alertas ---
    alertas = metadados.get("alertas", [])
    if alertas:
        for alerta in alertas:
            st.warning(f"⚠️ {alerta}")

    # --- Métricas resumo ---
    stats = metadados.get("stats", {})

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Registros processados", stats.get("total_apos_validacao", "—"))
    col2.metric("Overrides aplicados", stats.get("override_corrigidos", 0))
    col3.metric(
        "Baixa confiança (Grupo)",
        stats.get("baixa_confianca_grupo", "—"),
        help="Predições com confiança < 70% — revisar com atenção",
    )
    col4.metric(
        "Baixa confiança (Complexidade)",
        stats.get("baixa_confianca_complexidade", "—"),
        help="Predições com confiança < 70% — revisar com atenção",
    )

    # --- Distribuição das predições ---
    st.markdown("**Distribuição das predições:**")
    col_grupo, col_complex = st.columns(2)

    with col_grupo:
        st.markdown("*Grupo SUS:*")
        dist_grupo = df["PREVISAO_GRUPO"].value_counts()
        st.dataframe(dist_grupo, use_container_width=True)

    with col_complex:
        st.markdown("*Complexidade SUS:*")
        dist_complex = df["PREVISAO_COMPLEXIDADE"].value_counts()
        st.dataframe(dist_complex, use_container_width=True)

    # --- Avaliação (se gabarito existir) ---
    avaliacao = metadados.get("avaliacao")
    if avaliacao:
        with st.expander("📊 Relatório de avaliação (gabarito disponível)"):
            for modelo_nome, report in avaliacao.items():
                st.markdown(f"**{modelo_nome}**")
                accuracy = report.get("accuracy", 0)
                st.metric(f"Acurácia {modelo_nome}", f"{accuracy:.1%}")
                # Converte o dict do classification_report em DataFrame legível
                report_df = pd.DataFrame(report).transpose()
                st.dataframe(report_df.round(3), use_container_width=True)

    # --- Preview da tabela ---
    with st.expander("👁️ Preview dos dados (primeiras 20 linhas)"):
        colunas_preview = [
            "atendimento", "idade", "nr_dias", "sexo",
            "cid_1_principal", "cirurgia",
            "PREVISAO_GRUPO", "CONFIANCA_GRUPO",
            "PREVISAO_COMPLEXIDADE", "CONFIANCA_COMPLEXIDADE",
        ]
        # Filtra só as colunas que existem (pra não quebrar)
        colunas_disponiveis = [c for c in colunas_preview if c in df.columns]
        st.dataframe(df[colunas_disponiveis].head(20), use_container_width=True)

    # --- Download ---
    st.divider()
    st.subheader("5. Download")

    # Gera o Excel em memória (sem salvar em disco)
    buffer = io.BytesIO()
    df.to_excel(buffer, index=False, engine="openpyxl")
    buffer.seek(0)

    nome_arquivo = f"Banco Epidemio - {mes_ref}.xlsx"

    st.download_button(
        label=f"📥 Baixar planilha com predições ({nome_arquivo})",
        data=buffer,
        file_name=nome_arquivo,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
        use_container_width=True,
    )

    st.caption(
        "A planilha contém todas as colunas originais + PREVISAO_GRUPO, "
        "PREVISAO_COMPLEXIDADE, CONFIANCA_GRUPO e CONFIANCA_COMPLEXIDADE."
    )


# ---------------------------------------------------------------------------
# ABA 2: ENVIAR CORREÇÕES (Fase 2 — placeholder)
# ---------------------------------------------------------------------------
def aba_enviar_correcoes():
    """Placeholder para a Fase 2 (Ciclo HITL Automatizado)."""
    st.header("📤 Enviar Correções")
    st.info(
        "Esta funcionalidade será habilitada na próxima versão.\n\n"
        "Aqui você poderá enviar a planilha corrigida de volta ao sistema, "
        "que irá:\n"
        "- Detectar as diferenças entre a predição e a sua correção\n"
        "- Calcular a taxa de correção\n"
        "- Registrar os metadados de auditoria\n"
        "- Atualizar a base de dados para retreino futuro do modelo"
    )


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main():
    if not verificar_autenticacao():
        return

    # Sidebar com informações
    with st.sidebar:
        st.title("🏥 Classificação SUS")
        st.caption(f"v1.0 — {settings.app_titulo}")
        st.divider()
        st.markdown("**Operação:**")
        st.markdown(
            "1. Faça upload das 3 planilhas\n"
            "2. Verifique a validação\n"
            "3. Gere as predições\n"
            "4. Baixe o resultado\n"
            "5. Corrija no Excel e reenvie (em breve)"
        )
        st.divider()
        if st.button("🚪 Sair"):
            st.session_state.clear()
            st.rerun()

    # Abas
    tab1, tab2 = st.tabs(["📋 Gerar Predições", "📤 Enviar Correções"])

    with tab1:
        aba_gerar_predicoes()

    with tab2:
        aba_enviar_correcoes()


if __name__ == "__main__":
    main()