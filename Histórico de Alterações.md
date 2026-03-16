# Histórico de Alterações (Changelog) - Projeto Classificação SUS

Este documento registra as principais mudanças no script de classificação.

---
## v4.1 (Março de 2026)
* **Assunto:** Modularização (API/GUI Ready) e Correção de Multiplicação de Entradas (Bugfix).
* **Mudança:** Refatoração completa do script `gerar_previsoes.py` e correção da lógica de junção (*merge*) das cirurgias.
* **Motivo:** O script possuía variáveis "chumbadas" (hardcoded) que impediam a automação, e o cruzamento com pacientes que possuíam mais de uma cirurgia principal estava duplicando linhas na base final (A "Armadilha do PROCV").
* **Ação:**
    1. **Modularização:** Envelopamento da rotina principal na função `processar_previsoes()`, parametrizando os arquivos de entrada e saída.
    2. **Orquestração:** Adição do bloco de execução `if __name__ == '__main__':` para permitir que o código seja importado por outros sistemas (como Streamlit ou FastAPI) sem autoexecução.
    3. **Bugfix (Duplicidade):** Inclusão de um `drop_duplicates` focado no 'ATENDIMENTO' na base de cirurgias *antes* de realizar o `pd.merge` com a base principal.
    4. **Filtro de Ferro:** Implementação de auditoria com `.isin()` para identificar e ejetar pacientes intrusos de outros hospitais presentes no arquivo do MV Soul.
* **Resultado:** Código 100% desacoplado e pronto para a criação da Interface Visual, gerando uma base de saídas matematicamente exata em relação às altas físicas do hospital.

---
## v4.0 (Março de 2026)
* **Assunto:** Enriquecimento Semântico e Generalização por CID.
* **Mudança:** Integração do dicionário oficial de Categorias de CIDs (`Categorias de CIDs.xlsx`) ao pipeline de Feature Engineering.
* **Motivo:** A técnica anterior (extração da primeira letra do CID) era limitada. Ao injetar o "Capítulo" e o "Grupo" real da doença, o modelo ganha capacidade de generalizar padrões médicos, aumentando a acurácia em CIDs raros que a IA nunca "viu" isoladamente.
* **Ação:**
    1. Implementação de `pd.merge` (Left Join) no script `preparo_ml.py` com sanitização de strings (strip, upper).
    2. Substituição da feature `capitulo_cid` (derivada) pelas colunas oficiais `CAPÍTULO BREVE` e `GRUPO` no `executar_treino.py`.
    3. Atualização das dependências (`openpyxl`) para suporte à leitura de dicionários em Excel.
* **Resultado esperado:** Redução do erro em casos clínicos complexos e maior estabilidade do modelo frente a novos códigos de diagnóstico.

---
## v3.0 (Novembro de 2025)
* **Assunto:** Otimização de Performance e Combate ao "Data Drift".
* **Mudança:** O script principal (`script_classificacao_sus_otimizado_v3.py`) foi modificado para filtrar o histórico de treinamento.
* **Motivo:** A análise de distribuição temporal (feita em Outubro) provou que o perfil do `grupo_sus` mudou significativamente desde 2012, enquanto a `complexidade_sus` se manteve estável.
* **Ação:** O script agora treina os modelos **apenas com dados de 2020 em diante**.
* **Resultado:** A performance dos modelos aumentou drasticamente (ex: precisão da Alta Complexidade de 73% para 89% e F1-score do Grupo SUS de 0.63 para 0.87).

---
## v2.0 (Setembro de 2025)
* **Assunto:** Implementação do Balanceamento de Classes.
* **Mudança:** Introduzida a biblioteca `imbalanced-learn` e a técnica **SMOTE** no pipeline de treinamento.
* **Motivo:** O modelo original (v1.0) tinha baixo recall (56%) para "Alta Complexidade".
* **Ação:** O pipeline foi refeito para usar `ImbPipeline` e `SMOTE`, e foram adicionadas etapas de limpeza de "classes raras" (com < 10 membros) para estabilizar o treinamento.
* **Resultado:** O recall da "Alta Complexidade" saltou de 56% para 84%, melhorando drasticamente a utilidade do modelo.

---
## v1.0 (Setembro de 2025)
* **Assunto:** Modelo Base e Regra de Negócio.
* **Mudança:** Versão inicial do script.
* **Funcionalidades:**
    1.  Treinamento de dois modelos `LightGBM` (Grupo e Complexidade) com todos os dados históricos (2012+).
    2.  Geração de predições em novos arquivos.
    3.  Implementação de uma "camada de correção" (regra de negócio) na Parte B para forçar a classificação "cirúrgico" em casos onde um código de cirurgia estava presente.