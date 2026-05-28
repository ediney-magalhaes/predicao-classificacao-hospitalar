import pandas as pd
import logging
from config.settings import settings

logger = logging.getLogger(__name__)

def limpar_dados_historicos(df, ano_corte=2020):
    df_filtro = df[df['ano'] >= ano_corte]
    colunas_principais = ['grupo_sus', 'complexidade_sus', 'idade', 'sexo', 'nr_dias']
    df_limpo = df_filtro.dropna(subset=colunas_principais)
    return df_limpo


def engenharia_features(df):
    #lendo dicionário CIDs
    df_dict_cid = pd.read_excel(settings.dicionario_cid_path)[['CÓDIGO CID', 'CAPÍTULO BREVE', 'GRUPO']]
    #limpando a coluna do código do cid no dicionário
    df_dict_cid['CÓDIGO CID'] = df_dict_cid['CÓDIGO CID'].astype(str).str.upper().str.strip()
    #extraindo só o código CID para merge (preserva cid_1_principal original)
    df['_cid_merge'] = (
        df['cid_1_principal'].astype(str).str.upper().str.strip()
        .str.split(r'\s*-\s*').str[0].str.strip()
    )
    #fazendo merge com os dois datasets
    df_resultado = pd.merge(df, df_dict_cid, left_on='_cid_merge', right_on='CÓDIGO CID', how='left')
    df_resultado = df_resultado.drop(columns=['CÓDIGO CID', '_cid_merge'])
    return df_resultado

def remover_classes_raras(df, min_samples=10):
    for col in ['grupo_sus', 'complexidade_sus']:
        contar = df[col].value_counts()
        remover = contar[contar < min_samples].index
        if not remover.empty:
            logger.warning(f"Removendo {len(remover)} classes raras da coluna '{col}': {list(remover)}")
            df = df[~df[col].isin(remover)]
    return df