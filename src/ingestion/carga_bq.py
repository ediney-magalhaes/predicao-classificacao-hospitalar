import os
import pandas_gbq
from dotenv import load_dotenv
from google.oauth2 import service_account

load_dotenv()


def enviar_para_bigquery(df):
    projeto_saidas_hospitalares = os.getenv('GCP_PROJECT_ID')
    destino = 'dados_saidas_hospitalares.saidas_anonimizadas'
    caminho_chave = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')

    credenciais = service_account.Credentials.from_service_account_file(caminho_chave)


    pandas_gbq.to_gbq(dataframe= df, destination_table=destino, project_id=projeto_saidas_hospitalares, if_exists='replace')
    print("Dados enviados com sucesso para o BigQuery!")