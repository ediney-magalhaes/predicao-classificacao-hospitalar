import hashlib
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()

def anonimizar_nome(texto):
    if pd.isna(texto):
        return None

    texto = str(texto)
    salt = os.getenv('SALT_SUS','')
    texto_com_salt = texto + salt
    nova = texto_com_salt.encode('utf-8')
    return hashlib.sha256(nova).hexdigest()

def anonimizar_DataFrame(df):
    df['hash_paciente'] = df['nome_paciente'].apply(anonimizar_nome)
    df['hash_cpf'] = df['nr_cpf'].apply(anonimizar_nome)
    df = df.drop(columns=['nome_paciente','nr_cpf','endereco','cep','bairro','telefone'], errors='ignore')
    df.columns = df.columns.str.lower().str.replace(' ','_').str.replace('[^a-z0-9_]','', regex=True)
    return df
