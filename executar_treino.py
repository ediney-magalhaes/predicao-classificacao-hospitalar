import pandas as pd
import pandas_gbq
import joblib
import os

from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
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
    df_treino, df_teste = train_test_split(df_historico, test_size=0.2, random_state=42)
    modelo_grupo = treinar_modelo(df_treino, 'grupo_sus')
    joblib.dump(modelo_grupo, 'modelo_grupo_sus.joblib')
    previsoes_prova_grupo = modelo_grupo.predict(df_teste)
    texto_relatorio_grupo = classification_report(df_teste['grupo_sus'], previsoes_prova_grupo)
    with open('relatorio_performance.txt', 'w') as arquivo:
        arquivo.write('=== RELATORIO GRUPO SUS ===\n')
        arquivo.write(texto_relatorio_grupo)
    
    print("Modelo de GRUPO SUS treinado e salvo com sucesso!")

    #treinamento da classificação para a complexidade
    df_treino, df_teste = train_test_split(df_historico, test_size=0.2, random_state=42)
    modelo_complexidade = treinar_modelo(df_treino, 'complexidade_sus')
    joblib.dump(modelo_complexidade, 'modelo_complexidade_sus.joblib')
    previsoes_prova_complexidade = modelo_complexidade.predict(df_teste)
    texto_relatorio_complexidade = classification_report(df_teste['complexidade_sus'], previsoes_prova_complexidade)
    with open('relatorio_performance.txt','a') as arquivo:
        arquivo.write('\n=== RELATORIO COMPLEXIDADE SUS===\n')
        arquivo.write(texto_relatorio_complexidade)
    print("Modelo de COMPLEXIDADE SUS treinado e salvo com sucesso!")