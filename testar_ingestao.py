import pandas as pd
from src.ingestion.anonimizacao import anonimizar_DataFrame

altas_simuladas = {
    'nome_paciente': ['Ediney José da Silva', 'Rogério Oliveira Carvalho', None],
    'nr_cpf': ['00397651139', None, '00011133399'],
    'endereco': ['Rua Adel Maluf', 'Avenida 5', 'travessa 4'],
    'telefone': ['99920080', '36188285', '9898656535']
}

df_teste = pd.DataFrame(altas_simuladas)
print('------ BASE ORIGINAL ------')
print(df_teste)

df_anonimizado = anonimizar_DataFrame(df_teste)

print('------ BASE ANONIMIZADA ------')
print(df_anonimizado)
