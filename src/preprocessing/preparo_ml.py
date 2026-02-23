import pandas as pd

def limpar_dados_historicos(df, ano_corte=2020):
    df_filtro = df[df['ano'] >= ano_corte]
    colunas_principais = ['grupo_sus', 'complexidade_sus', 'idade', 'sexo', 'nr_dias']
    df_limpo = df_filtro.dropna(subset=colunas_principais)
    return df_limpo


def engenharia_features(df):
    if 'cid_1_principal' in df.columns:
        df['capitulo_cid'] = df['cid_1_principal'].astype(str).str[0]
    return df

def remover_classes_raras(df, min_samples=10):
    for col in ['grupo_sus', 'complexidade_sus']:
        contar = df[col].value_counts()
        remover = contar[contar < min_samples].index
        if not remover.empty:
            print(f"Removendo {len(remover)} classes raras da coluna '{col}': {list(remover)}")
            df = df[~df[col].isin(remover)]
    return df