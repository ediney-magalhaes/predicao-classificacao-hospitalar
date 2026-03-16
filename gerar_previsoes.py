import pandas as pd
import openpyxl
import joblib
from sklearn.metrics import classification_report
from src.preprocessing.preparo_ml import engenharia_features


def processar_previsoes(altas_mes_previsao, cirurgias_mes_previsao,
                        saidas_mes_previsao, arquivo_previsoes):
      
      #lendo banco de dados de saídas
      df_saidas = pd.read_excel(saidas_mes_previsao)

      #contando o tamanho do banco de dados
      print(f'A base continha {len(df_saidas)} linhas')
      
      #excluindo os atendimentos duplicados
      df_saidas = df_saidas.drop_duplicates(subset=['ATENDIMENTO'])
      print(f'Com a desduplicação a base contém {len(df_saidas)} linhas')
      
      #lendo banco de dados de saídas do MV
      df_saidas_MV = pd.read_excel(altas_mes_previsao)
      
      #conferindo a quantidade de altas do sistema MV com a planilha de altas
      atend_planilha = set(df_saidas['ATENDIMENTO'])
      atend_sistema_MV = set(pd.to_numeric(df_saidas_MV.iloc[:,1], errors='coerce').dropna())
      diferenca = atend_sistema_MV - atend_planilha
      intrusos = atend_planilha - atend_sistema_MV
      df_saidas = df_saidas[df_saidas['ATENDIMENTO'].isin(atend_sistema_MV)]
      if len(diferenca) == 0:
          print('Sucesso! Não há diferenças de pacientes entre as planilhas.')
      else:
          print(f'ATENÇÃO! A planilha está incompleta. Faltam os seguintes atendimentos do MV: {diferenca}')
      
      if len(intrusos) != 0:
          print(f'Atenção aos pacientes de outro hospital que estavam na planilha: {intrusos}')
      
      #excluir a coluna de "COD_CID_SUMARIO"
      df_saidas = df_saidas.drop(columns=['COD_CID_SUMARIO'])
      print('Coluna COD_CID_SUMARIO excluída!')
      
      #preencher a coluna CID_1_PRINCIPAL
      df_saidas['CID_1_PRINCIPAL'] = df_saidas['CID_1_PRINCIPAL'].fillna(df_saidas['CID_ENTRADA'])
      
      #recebendo a base de cirurgias
      df_cirurgias_realizadas = pd.read_excel(cirurgias_mes_previsao)

      #filtrando apenas as cirurgias principais
      df_cirurgias_realizadas = df_cirurgias_realizadas[df_cirurgias_realizadas['SN_PRINCIPAL'] == 'SIM']

      #excluindo cirurgias principais duplicadas
      df_cirurgias_realizadas = df_cirurgias_realizadas.drop_duplicates(subset=['ATENDIMENTO'])
      print(f'Com a desduplicação a base contém {len(df_cirurgias_realizadas)} linhas')

      #aplicando merge entre as planilhas para verificar quem fez cirurgias
      df_saidas = pd.merge(df_saidas,df_cirurgias_realizadas[['ATENDIMENTO','DESCRICAO_CIRURGIA']], on='ATENDIMENTO', how='left')

      #tornando os nomes da colunas em minusculo
      df_saidas.columns = df_saidas.columns.str.lower()

      #cruzando base com o Dicionário de CIDs
      df_saidas = engenharia_features(df_saidas)

      #renomeando a coluna com nome das cirurgias
      df_saidas = df_saidas.rename(columns={'descricao_cirurgia': 'cirurgia'})

      # preenchendo as cirurgias vazias antes da previsão
      df_saidas['cirurgia'] = df_saidas['cirurgia'].fillna('DESCONHECIDO')

      #carregando modelo de previsões para o GRUPO_SUS
      previsao_grupo_SUS = joblib.load('modelo_grupo_sus.joblib')

      #carregando modelo de previsões para o Complexidade_SUS
      previsao_complexidade_SUS = joblib.load('modelo_complexidade_sus.joblib')

      ##criando coluna de previsões do grupo SUS
      df_saidas['PREVISAO_GRUPO'] = previsao_grupo_SUS.predict(df_saidas[['idade', 'nr_dias', 'cid_entrada',
                                                  'procedimento_entrada', 'CAPÍTULO BREVE', 'GRUPO', 'cirurgia',
                                                  'cid_1_principal', 'sexo' , 'medico_resp_atend']])
      
      ##criando coluna de previsões do complexidade SUS
      df_saidas['PREVISAO_COMPLEXIDADE'] = previsao_complexidade_SUS.predict(df_saidas[['idade', 'nr_dias', 'cid_entrada',
                                                  'procedimento_entrada', 'cid_1_principal', 'cirurgia',
                                                  'CAPÍTULO BREVE', 'GRUPO', 'sexo' , 'medico_resp_atend']])
      
      print("Aplicando regra de negócio de override para 'Cirurgia'...")
      valores_nao_cirurgicos = ['DESCONHECIDO', 'NAO_CIRURGICO', 'nan', '', '-']

      # Verifica quem tem cirurgia e onde a IA disse que era 'Clínico'
      condicao_cirurgia = ~df_saidas['cirurgia'].astype(str).isin(valores_nao_cirurgicos)
      condicao_erro = (df_saidas['PREVISAO_GRUPO'] == 'Procedimentos clínicos')
      indices_corrigir = df_saidas[condicao_cirurgia & condicao_erro].index

      if len(indices_corrigir) > 0:
          print(f"Corrigindo {len(indices_corrigir)} previsões onde a regra de cirurgia foi ignorada pela IA...")
          df_saidas.loc[indices_corrigir, 'PREVISAO_GRUPO'] = 'Procedimentos cirúrgicos'
      else:
          print("Nenhuma correção de regra de negócio foi necessária.")

      # --- GERANDO RELATÓRIOS DE AVALIAÇÃO ---
      # Verifica se a base possui o gabarito real para calcular a precisão
      if 'grupo_sus' in df_saidas.columns and 'complexidade_sus' in df_saidas.columns:
          print("\nRelatório de Avaliação para GRUPO_SUS (Janeiro):")
          print(classification_report(df_saidas['grupo_sus'], df_saidas['PREVISAO_GRUPO'], zero_division=0))
          print("\nRelatório de Avaliação para COMPLEXIDADE_SUS (Janeiro):")
          print(classification_report(df_saidas['complexidade_sus'], df_saidas['PREVISAO_COMPLEXIDADE'], zero_division=0))
      else:
          print("\nColunas reais (grupo_sus / complexidade_sus) não encontradas. Impossível gerar Acurácia.")
          print("\nDistribuição Prevista (Volume de Janeiro):")
          print(df_saidas['PREVISAO_GRUPO'].value_counts())
      
      # salvando a base final
      df_saidas.to_excel(arquivo_previsoes, index=False)
      
      #abrindo relatório de performance do modelo
      with open('relatorio_performance.txt', 'r') as arquivo:
          print(arquivo.read())


if __name__ == '__main__':
    processar_previsoes('ALTAS.xlsx', 'Cirurgias Realizadas 02-2026.xlsx', 'EPIDEMIO 02 2026.xlsx', 'Banco Epidemio - Fevereiro 2026.xlsx')