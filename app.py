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
from src.hitl.pipeline_correcao import salvar_predicao_original, processar_correcao
from src.ingestion.ingestao_movimentacoes import processar_movimentacoes
from src.ingestion.ingestao_financeiro import processar_valor_conta

# LOGGING
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# CONFIGURAÇÃO DA PÁGINA
st.set_page_config(
    page_title=settings.app_titulo,
    page_icon="🏥",
    layout="wide",
)

# AUTENTICAÇÃO
# Senha simples via st.secrets. O arquivo .streamlit/secrets.toml
# contém: senha = "sua_senha_aqui"
# Na Fase 8 (industrialização), isso evolui pra autenticação mais robusta.
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

# ABA 1: GERAR PREDIÇÕES
def aba_gerar_predicoes():
    """Fluxo principal: upload → validação → predição → download."""

    st.header("📋 Gerar Predições")
    st.markdown(
        "Faça upload das 3 planilhas do mês, valide os dados "
        "e gere as predições de Grupo e Complexidade SUS."
    )

    # seleção do mês de referência
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

    # upload dos 3 arquivos
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

    # validação
    if arquivo_saidas and arquivo_altas and arquivo_cirurgias:
        st.subheader("2. Validação dos dados")

        # leitura dos DataFrames
        try:
            df_saidas = pd.read_excel(arquivo_saidas)
            df_altas = pd.read_excel(arquivo_altas)
            df_cirurgias = pd.read_excel(arquivo_cirurgias)
        except Exception as e:
            st.error(f"Erro ao ler os arquivos: {e}")
            return

        # validação de cada planilha
        resultados_validacao = []

        ok_saidas, msg_saidas = validar_saidas(df_saidas)
        ok_altas, msg_altas = validar_altas(df_altas)
        ok_cirurgias, msg_cirurgias = validar_cirurgias(df_cirurgias)

        # exibe resultado da validação
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

        # predição
        st.subheader("3. Gerar predições")

        if st.button("🚀 Gerar Predições", type="primary", use_container_width=True):
            with st.spinner("Processando predições... Isso pode levar alguns segundos."):
                try:
                    df_resultado, metadados = processar_previsoes(
                        df_saidas, df_altas, df_cirurgias
                    )
                    # salva no session_state pra sobreviver ao rerun
                    st.session_state["df_resultado"] = df_resultado
                    st.session_state["metadados"] = metadados
                    st.session_state["mes_ref"] = f"{mes:02d}-{ano}"
                    logger.info(f"Predição concluída para {mes:02d}/{ano}")
                    
                    # salva predição original na W: para comparação
                    safra = f"{ano}-{mes:02d}"
                    caminho_salvo = salvar_predicao_original(df_resultado, safra)
                    if caminho_salvo:
                        st.session_state["caminho_predicao_original"] = str(caminho_salvo)
                        logger.info(f"Predição original salva em: {caminho_salvo}")
                    else:
                        logger.warning("Não foi possível salvar predição original na W:")
                except Exception as e:
                    st.error(f"Erro durante o processamento: {e}")
                    logger.exception("Erro no processamento de predições")
                    return

        # resultado
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

    # alertas
    alertas = metadados.get("alertas", [])
    if alertas:
        for alerta in alertas:
            st.warning(f"⚠️ {alerta}")

    # lista de atendimentos faltantes (constam no MV mas não na epidemio)
    lista_faltantes = metadados.get("stats", {}).get("lista_faltantes_mv", [])
    if lista_faltantes:
        with st.expander(f"📋 {len(lista_faltantes)} atendimentos para buscar no MV"):
            st.markdown(
                "Esses atendimentos constam nas altas do MV mas **não foram encontrados** "
                "na planilha Epidemio. Busque no sistema e adicione manualmente na planilha "
                "antes de enviar as correções."
            )
            st.dataframe(
                {"Nº Atendimento": lista_faltantes},
                use_container_width=True,
                hide_index=True,
            )

    # métricas resumo
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

    # distribuição das predições
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

    # avaliação (se gabarito existir)
    avaliacao = metadados.get("avaliacao")
    if avaliacao:
        with st.expander("📊 Relatório de avaliação (gabarito disponível)"):
            for modelo_nome, report in avaliacao.items():
                st.markdown(f"**{modelo_nome}**")
                accuracy = report.get("accuracy", 0)
                st.metric(f"Acurácia {modelo_nome}", f"{accuracy:.1%}")
                # converte o dict do classification_report em DataFrame legível
                report_df = pd.DataFrame(report).transpose()
                st.dataframe(report_df.round(3), use_container_width=True)

    # preview da tabela
    with st.expander("👁️ Preview dos dados (primeiras 20 linhas)"):
        colunas_preview = [
            "atendimento", "idade", "nr_dias", "sexo",
            "cid_1_principal", "cirurgia",
            "PREVISAO_GRUPO", "CONFIANCA_GRUPO",
            "PREVISAO_COMPLEXIDADE", "CONFIANCA_COMPLEXIDADE",
        ]
        # filtra só as colunas que existem
        colunas_disponiveis = [c for c in colunas_preview if c in df.columns]
        st.dataframe(df[colunas_disponiveis].head(20), use_container_width=True)

    # download
    st.divider()
    st.subheader("5. Download")

    # gera excel em memória (sem salvar em disco)
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

# ABA 2: ENVIAR CORREÇÕES
def aba_enviar_correcoes():
    """Fluxo de envio de correções: upload → validação → comparação → ingestão."""

    st.header("📤 Enviar Correções")
    st.markdown(
        "Após revisar e corrigir as predições no Excel, "
        "faça upload da planilha corrigida aqui."
    )

    # seleção do mês de referência
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
            key="correcao_mes",
        )
    with col_ano:
        ano = st.selectbox(
            "Ano:",
            options=list(range(2025, datetime.now().year + 1)),
            index=min(datetime.now().year - 2025, 1),
            key="correcao_ano",
        )

    st.divider()

    # upload da planilha revisada
    arquivo_revisado = st.file_uploader(
        "📄 Planilha revisada (com correções)",
        type=["xlsx"],
        key="upload_revisado",
        help="O arquivo que você corrigiu no Excel após revisar as predições",
    )

    arquivo_movimentacoes = st.file_uploader(
    "📄 Relatório de Movimentações",
    type=["xlsx"],
    key="upload_movimentacoes",
    help="Relatório bruto de movimentações exportado do sistema, salvo em Excel (sem tratamento)",
    )

    if arquivo_revisado and arquivo_movimentacoes:
        try:
            df_revisado = pd.read_excel(arquivo_revisado)
            df_movimentacoes = pd.read_excel(arquivo_movimentacoes, header=None)
        except Exception as e:
            st.error(f"Erro ao ler o arquivo: {e}")
            return

        st.success(
            f"Arquivos carregados: {len(df_revisado)} registros de correção, "
            f"{len(df_movimentacoes)} registros de movimentações"
        )

        safra = f"{ano}-{mes:02d}"

        # botão de processar
        if st.button("🚀 Processar Correções", type="primary", use_container_width=True):
            with st.spinner("Processando correções... Validando, comparando e enviando."):
                resultado = processar_correcao(
                    df_revisado=df_revisado,
                    safra_mes=safra,
                    revisor="assistente_epidemio",
                )
            with st.spinner("Processando movimentações... Validando e enviando."):
                resultado_movimentacoes = processar_movimentacoes(
                    df_movimentacoes=df_movimentacoes,
                    safra_mes=safra,
                )

            # exibir resultado
            if resultado["sucesso"]:
                st.success(f"✅ {resultado['mensagem']}")

                # métricas de correção (se disponíveis)
                metricas = resultado.get("metricas")
                if metricas and metricas.get("total_registros"):
                    st.divider()
                    st.subheader("Resumo das correções")

                    col1, col2, col3 = st.columns(3)
                    col1.metric(
                        "Correções em Grupo",
                        metricas.get("correcoes_grupo", 0),
                        help="Quantidade de linhas onde PREVISAO_GRUPO foi alterado",
                    )
                    col2.metric(
                        "Correções em Complexidade",
                        metricas.get("correcoes_complexidade", 0),
                        help="Quantidade de linhas onde PREVISAO_COMPLEXIDADE foi alterado",
                    )
                    col3.metric(
                        "Correções em ambas",
                        metricas.get("correcoes_ambos", 0),
                        help="Linhas onde ambas as colunas foram corrigidas",
                    )

                    # taxas de correção
                    col4, col5 = st.columns(2)
                    col4.metric(
                        "Taxa de correção (Grupo)",
                        f"{metricas.get('taxa_correcao_grupo', 0):.1f}%",
                    )
                    col5.metric(
                        "Taxa de correção (Complexidade)",
                        f"{metricas.get('taxa_correcao_complexidade', 0):.1f}%",
                    )

                    # detalhamento das transições
                    for chave in ["detalhamento_grupo", "detalhamento_complexidade"]:
                        transicoes = metricas.get(chave, [])
                        if transicoes:
                            nome = chave.replace("detalhamento_", "").title()
                            with st.expander(f"Detalhamento — {nome}"):
                                df_trans = pd.DataFrame(transicoes)
                                df_trans.columns = ["De (modelo)", "Para (revisão)", "Quantidade"]
                                st.dataframe(df_trans, use_container_width=True)

                # registros enviados
                if resultado.get("registros_enviados"):
                    st.info(
                        f"📊 {resultado['registros_enviados']} registros anonimizados "
                        f"enviados para a base de treino."
                    )
            else:
                st.error(f"❌ Falha na etapa: **{resultado['etapa_falha']}**")
                st.markdown(resultado["mensagem"])

            st.divider()

            if resultado_movimentacoes["sucesso"]:
                st.success(f"✅ {resultado_movimentacoes['mensagem']}")
            else:
                st.error(f"❌ Falha na etapa: **{resultado_movimentacoes['etapa_falha']}**")
                st.markdown(resultado_movimentacoes["mensagem"])
    else:
        st.info("Faça upload da planilha revisada para continuar.")

# ABA 3: FINANCEIRO
def aba_enviar_financeiro():
    """Fluxo de envio da base dos valores da conta."""

    st.header("💰 Enviar Financeiro")
    st.markdown(
        "Faça upload da planilha baixada do Qlikview aqui."
    )

    arquivo_financeiro = st.file_uploader(
        "📄 Relatório Análise de Contas",
        type=["xlsx"],
        key="upload_financeiro",
        help="Relatório de análise das contas exportado do Qlikview, salvo em Excel (sem tratamento)",
        )

    if arquivo_financeiro:
        try:
            df_financeiro = pd.read_excel(arquivo_financeiro)
        except Exception as e:
            st.error(f"Erro ao ler o arquivo: {e}")
            return

        st.success(
            f"Arquivo carregado: {len(df_financeiro)} registros das contas hospitalares "
        )

        # botão de processar
        if st.button("🚀 Processar Financeiro", type="primary", use_container_width=True):
            with st.spinner("Processando... Validando e enviando."):
                resultado = processar_valor_conta(df_financeiro)

            # exibir resultado
            if resultado["sucesso"]:
                st.success(f"✅ {resultado['mensagem']}")
                st.info(f"📊 {resultado['registros_enviados']} registros anonimizados enviados")
            else:
                st.error(f"❌ Falha na etapa: **{resultado['etapa_falha']}**")
                st.markdown(resultado["mensagem"])
    else:
        st.info("Faça upload da planilha para continuar.")
        

# MAIN
def main():
    if not verificar_autenticacao():
        return

    # sidebar com informações
    with st.sidebar:
        st.title("🏥 Classificação SUS")
        st.caption(f"v2.0 — {settings.app_titulo}")
        st.divider()
        st.markdown("**Operação:**")
        st.markdown(
            "1. Faça upload das 3 planilhas\n"
            "2. Verifique a validação\n"
            "3. Gere as predições\n"
            "4. Baixe o resultado\n"
            "5. Corrija no Excel\n"
            "6. Reenvie na aba Correções"
        )
        st.divider()
        if st.button("🚪 Sair"):
            st.session_state.clear()
            st.rerun()

    # Abas
    tab1, tab2, tab3 = st.tabs(["📋 Gerar Predições", "📤 Enviar Correções", "💰 Financeiro"])

    with tab1:
        aba_gerar_predicoes()

    with tab2:
        aba_enviar_correcoes()

    with tab3:
        aba_enviar_financeiro()


if __name__ == "__main__":
    main()