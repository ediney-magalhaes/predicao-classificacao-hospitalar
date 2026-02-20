import pandas as pd
import pandas_gbq
import joblib
import os

from dotenv import load_dotenv
from google.oauth2 import service_account
from src.preprocessing.preparo_ml import limpar_dados_historicos, engenharia_features, remover_classes_raras
from src.modelagem.treinamento import treinar_modelo

if __name__ == '__main__':
    load_dotenv()
    #leitura do banco de dados
    projeto_saidas_hospitalares = os.getenv('GCP_PROJECT_ID')
    destino = 'dados_saidas_hospitalares.saidas_anonimizadas'
    caminho_chave = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    credenciais = service_account.Credentials.from_service_account_file(caminho_chave)
    
    #selecionando o projeto no BigQuery
    query = f"SELECT * FROM `{projeto_saidas_hospitalares}.{destino}`"
    
    #executar a query na nuvem
    df_historico = pandas_gbq.read_gbq(query, project_id=projeto_saidas_hospitalares, credentials=credenciais)
    print('Arquivo histórico carregado com sucesso!')
    print("\nColunas vindas do BigQuery:", df_historico.columns.tolist())

    #fazendo as limpezas no banco
    df_historico = limpar_dados_historicos(df_historico, ano_corte=2020)
    df_historico = engenharia_features(df_historico)
    df_historico = remover_classes_raras(df_historico)

    print(f"Dados limpos! Total de linhas: {len(df_historico)}")

    #treinamento da classificação para o Grupo (SUS)
    modelo_grupo = treinar_modelo(df_historico, 'grupo_sus')
    joblib.dump(modelo_grupo, 'modelo_grupo_sus.joblib')
    print("Modelo de GRUPO SUS treinado e salvo com sucesso!")

    #treinamento da classificação para a complexidade
    modelo_complexidade = treinar_modelo(df_historico, 'complexidade_sus')
    joblib.dump(modelo_complexidade, 'modelo_complexidade_sus.joblib')
    print("Modelo de COMPLEXIDADE SUS treinado e salvo com sucesso!")