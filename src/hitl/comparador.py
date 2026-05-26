"""
Comparador de predições vs revisões humanas.

Este módulo pareia o arquivo de predição original (gerado pelo modelo)
com o arquivo revisado pela assistente, e calcula métricas de correção.

Essas métricas alimentam:
  - A GUI (assistente vê resumo antes de confirmar envio)
  - A tabela de auditoria (audit.hitl_events no BigQuery)
  - O dashboard de performance do modelo (Fase 3/4)
"""

import pandas as pd

def calcular_diferencas(
        df_original: pd.DataFrame,
        df_revisao: pd.DataFrame,
        coluna_chave: str="ATENDIMENTO",
        colunas_comparar: list[str] | None = None
        ) -> dict:
    """
    Compara predições originais com revisões humanas.

    Pareia os dois DataFrames pela coluna chave (ATENDIMENTO),
    compara as colunas de predição e calcula métricas de correção.

    Args:
        df_original: DataFrame com predições do modelo.
        df_revisado: DataFrame após revisão da assistente.
        coluna_chave: Coluna usada para parear registros.
        colunas_comparar: Colunas a comparar. Se None, usa as duas
                          colunas padrão de predição.

    Returns:
        Dicionário com métricas de correção:
        {
            "total_registros": int,
            "correcoes_grupo": int,
            "correcoes_complexidade": int,
            "correcoes_ambos": int,
            "taxa_correcao_grupo": float,
            "taxa_correcao_complexidade": float,
            "detalhamento_grupo": dict,
            "detalhamento_complexidade": dict
        }
    """
    # verifica se as colunas de comparação existem
    if colunas_comparar is None:
        colunas_comparar = ["PREVISAO_GRUPO", "PREVISAO_COMPLEXIDADE"]
    
    # pareamento pelo número de atendimento
    df_merge = df_original.merge(
        df_revisao[[coluna_chave] + colunas_comparar],
        on=coluna_chave,
        suffixes=("_modelo", "_revisado")
    )

    total = len(df_merge)
    resultado = {"total_registros": total}

    # calcula a diferenças por colunas
    for coluna in colunas_comparar:
        col_modelo = f"{coluna}_modelo"
        col_revisado = f"{coluna}_revisado"

        # verifica linhas que houve alterações (correções)
        diferencas = df_merge[col_modelo] != df_merge[col_revisado]
        qtd_correcoes = diferencas.sum()

        # nome para chave do dicionário
        nome_curto = coluna.replace("PREVISAO_", "").lower()

        resultado[f"correcoes_{nome_curto}"] = int(qtd_correcoes)
        resultado[f"taxa_correcao_{nome_curto}"] = round(
            qtd_correcoes / total * 100, 2
        ) if total > 0 else 0.0

        # detalhe de qual classe para qual classe foi feita a correção
        if qtd_correcoes > 0:
            transicoes = (
                df_merge[diferencas]
                .groupby([col_modelo, col_revisado])
                .size()
                .reset_index(name="contagem")
            )
            resultado[f"detalhamento_{nome_curto}"] = transicoes.to_dict("records")
        else:
            resultado[f"detalhamento_{nome_curto}"] = []
    
    # correções em ambas as colunas simultaneamente
    if len(colunas_comparar) == 2:
        col1, col2 = colunas_comparar
        ambas = (
            (df_merge[f"{col1}_modelo"] != df_merge[f"{col1}_revisado"]) &
            (df_merge[f"{col2}_modelo"] != df_merge[f"{col2}_revisado"])
        )
        resultado["correcoes_ambos"] = int(ambas.sum())
    else:
        resultado["correcoes_ambos"] = 0

    return resultado
