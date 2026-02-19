import pandas as pd
from src.preprocessing.preparo_ml import limpar_dados_historicos, engenharia_features, remover_classes_raras

dados_mock = {
    'ano': [2019, 2021, 2022, 2023, 2023], # O primeiro deve sumir pelo ano
    'grupo_sus': ['Comum', 'Comum', 'Comum', 'Comum', 'Rarissimo'], # O último deve sumir por ser raro
    'complexidade_sus': ['Alta', 'Alta', 'Media', None, 'Baixa'], # O penúltimo deve sumir pelo nulo
    'idade': [50, 45, 30, 60, 25],
    'sexo': ['M', 'F', 'F', 'M', 'F'],
    'nr_dias_internacao': [5, 2, 10, 3, 1],
    'cid_1_principal': ['J01', 'A09', 'I10', 'E11', 'O80'] # Devem virar 'J', 'A', 'I', 'E', 'O'
}
df_teste = pd.DataFrame(dados_mock)
print("--- BASE ORIGINAL ---")
print(df_teste)

df_1 = limpar_dados_historicos(df_teste, ano_corte=2020)
df_1 = engenharia_features(df_1)
df_1 = remover_classes_raras(df_1, min_samples=2)
print("\n--- BASE APÓS PRÉ-PROCESSAMENTO ---")
print(df_1)