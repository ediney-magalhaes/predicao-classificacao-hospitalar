
import pandas as pd
import lightgbm as lgb

from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline as ImbPipeline

from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer

from lightgbm import LGBMClassifier

#função para verificar existência de colunas
def existencia_feature(df, lista_features):
    return [f for f in lista_features if f in df.columns]

#função para treinamento do modelo
def treinar_modelo(df_treino, coluna_alvo):
    #definindo as variáveis
    y = df_treino[coluna_alvo]
    X = df_treino.drop(columns=['grupo_sus', 'complexidade_sus'], errors='ignore')
    
    #listas de features
    features_numericas= ['idade', 'nr_dias_internacao']
    features_categoricas= ['cid_entrada', 'procedimento_entrada', 'cid_1_principal', 'cirurgia', 'capitulo_cid', 'sexo' , 'medico_resp_atend']

    #processamento das features
    preprocessor = ColumnTransformer(transformers=[
        ('num', StandardScaler(), existencia_feature(X,features_numericas)),
        ('cat', OneHotEncoder(handle_unknown='ignore', drop='first'), existencia_feature(X, features_categoricas))],
        remainder='drop')

    #juntando as peças em um pipeline
    pipeline_final = ImbPipeline(steps=[('preprocessor', preprocessor),
                                        ('smote', SMOTE(random_state=42)),
                                        ('classifier', LGBMClassifier(random_state=42, n_jobs=-1))])
    
    #Ajustando o modelo (fit)
    pipeline_final.fit(X, y)
    return pipeline_final