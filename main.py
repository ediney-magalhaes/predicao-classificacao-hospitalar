import pandas as pd
from src.ingestion.anonimizacao import anonimizar_DataFrame
from src.ingestion.carga_bq import enviar_para_bigquery

caminho_arquivo = 'data/historico_saidas(ajustado).csv'

df_bruto = pd.read_csv(caminho_arquivo, encoding='latin-1', sep=';',low_memory=False)

df_limpo = anonimizar_DataFrame(df_bruto)

print(df_limpo.shape)
print(df_limpo.head())

enviar_para_bigquery(df_limpo)