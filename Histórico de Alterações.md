# Histórico de Alterações (Changelog) - Projeto Classificação SUS

Este documento registra as principais mudanças no sistema de classificação.

O projeto adota **Versionamento Semântico (SemVer)**: `MAJOR.MINOR.PATCH`
- **MAJOR:** mudança que quebra compatibilidade (nova arquitetura, mudança de interface)
- **MINOR:** funcionalidade nova sem quebra de compatibilidade
- **PATCH:** correção de bug ou ajuste menor

---

## v5.0.0 (Maio de 2026)
* **Assunto:** Refatoração Arquitetural + GUI Streamlit + Validação em Camadas.
* **Mudança:** Reestruturação completa do projeto — separação de I/O e lógica de negócio, introdução de configuração centralizada, módulo de inferência isolado, validação de entrada com Pandera, e interface gráfica para a assistente.
* **Motivo:** A assistente dependia do Ediney para rodar predições via terminal. O código monolítico misturava leitura de arquivos, processamento, predição e escrita num único script, dificultando reuso e evolução.
* **Ações:**
    1. **Configuração centralizada:** `config/settings.py` com Pydantic BaseSettings. Caminhos de modelos, listas de features, valores de override e colunas obrigatórias centralizados num único lugar. Variáveis sensíveis lidas do `.env` com validação na inicialização.
    2. **Módulo de inferência:** `src/inference/predicao.py` isola carregamento de modelos (com cache em memória), predição com confiança (`predict_proba`), e Business Rule Override. Funções internas prefixadas com `_` (encapsulamento).
    3. **Módulo de validação:** `src/validacao/validacao.py` com schemas Pandera para as 3 planilhas de entrada. Mensagens de erro formatadas para usuária não-técnica.
    4. **Orquestrador refatorado:** `gerar_previsoes.py` agora recebe DataFrames (não caminhos de arquivo) e retorna DataFrame + dict de metadados. Zero I/O na lógica de negócio. Adapter de terminal no `if __name__ == '__main__'`.
    5. **GUI Streamlit:** `app.py` com autenticação por senha, upload de 3 planilhas, validação automática, predição com métricas de confiança, alertas contextuais e download do XLSX. Duas abas (predição ativa + correções como placeholder para Fase 2).
    6. **Logging:** substituição de `print()` por `logging` em todos os módulos (info, warning, debug).
    7. **Governança:** estrutura `docs/` com ADRs (MADR), templates, runbooks e model cards. CONTRIBUTING.md atualizado com fluxo de ADRs.
* **Novas colunas de saída:** `CONFIANCA_GRUPO` e `CONFIANCA_COMPLEXIDADE` (max predict_proba por predição). Valores < 0.7 sinalizados como baixa confiança na GUI.
* **ADRs fechadas:** ADR-0001 (validação em camadas: Pydantic + Pandera + dbt), ADR-0002 (hosting da GUI local na rede hospitalar).
* **Stack adicionada:** Streamlit, Pydantic v2, Pandera.
* **Resultado:** Assistente opera autonomamente via navegador na rede do hospital. Pipeline testada end-to-end com dados reais (~820 registros processados, validação Pandera + predição + confiança + override em segundos).

---

## v4.1.0 (Março de 2026)
* **Assunto:** Modularização (API/GUI Ready) e Correção de Multiplicação de Entradas (Bugfix).
* **Mudança:** Refatoração completa do script `gerar_previsoes.py` e correção da lógica de junção (*merge*) das cirurgias.
* **Motivo:** O script possuía variáveis "chumbadas" (hardcoded) que impediam a automação, e o cruzamento com pacientes que possuíam mais de uma cirurgia principal estava duplicando linhas na base final (A "Armadilha do PROCV").
* **Ações:**
    1. **Modularização:** Envelopamento da rotina principal na função `processar_previsoes()`, parametrizando os arquivos de entrada e saída.
    2. **Orquestração:** Adição do bloco de execução `if __name__ == '__main__':` para permitir que o código seja importado por outros sistemas (como Streamlit ou FastAPI) sem autoexecução.
    3. **Bugfix (Duplicidade):** Inclusão de um `drop_duplicates` focado no 'ATENDIMENTO' na base de cirurgias *antes* de realizar o `pd.merge` com a base principal.
    4. **Filtro de Ferro:** Implementação de auditoria com `.isin()` para identificar e ejetar pacientes intrusos de outros hospitais presentes no arquivo do MV Soul.
* **Resultado:** Código 100% desacoplado e pronto para a criação da Interface Visual, gerando uma base de saídas matematicamente exata em relação às altas físicas do hospital.

---

## v4.0.0 (Março de 2026)
* **Assunto:** Enriquecimento Semântico e Generalização por CID.
* **Mudança:** Integração do dicionário oficial de Categorias de CIDs (`Categorias de CIDs.xlsx`) ao pipeline de Feature Engineering.
* **Motivo:** A técnica anterior (extração da primeira letra do CID) era limitada. Ao injetar o "Capítulo" e o "Grupo" real da doença, o modelo ganha capacidade de generalizar padrões médicos, aumentando a acurácia em CIDs raros que a IA nunca "viu" isoladamente.
* **Ações:**
    1. Implementação de `pd.merge` (Left Join) no script `preparo_ml.py` com sanitização de strings (strip, upper).
    2. Substituição da feature `capitulo_cid` (derivada) pelas colunas oficiais `CAPÍTULO BREVE` e `GRUPO` no `executar_treino.py`.
    3. Atualização das dependências (`openpyxl`) para suporte à leitura de dicionários em Excel.
* **Resultado:** Redução do erro em casos clínicos complexos e maior estabilidade do modelo frente a novos códigos de diagnóstico.

---

## v3.0.0 (Novembro de 2025)
* **Assunto:** Otimização de Performance e Combate ao "Data Drift".
* **Mudança:** O script principal foi modificado para filtrar o histórico de treinamento.
* **Motivo:** A análise de distribuição temporal (feita em Outubro) provou que o perfil do `grupo_sus` mudou significativamente desde 2012, enquanto a `complexidade_sus` se manteve estável.
* **Ação:** O script agora treina os modelos apenas com dados de 2020 em diante.
* **Resultado:** A performance dos modelos aumentou drasticamente (ex: precisão da Alta Complexidade de 73% para 89% e F1-score do Grupo SUS de 0.63 para 0.87).

---

## v2.0.0 (Setembro de 2025)
* **Assunto:** Implementação do Balanceamento de Classes.
* **Mudança:** Introduzida a biblioteca `imbalanced-learn` e a técnica SMOTE no pipeline de treinamento.
* **Motivo:** O modelo original (v1.0) tinha baixo recall (56%) para "Alta Complexidade".
* **Ação:** O pipeline foi refeito para usar `ImbPipeline` e `SMOTE`, e foram adicionadas etapas de limpeza de "classes raras" (com < 10 membros) para estabilizar o treinamento.
* **Resultado:** O recall da "Alta Complexidade" saltou de 56% para 84%, melhorando drasticamente a utilidade do modelo.

---

## v1.0.0 (Setembro de 2025)
* **Assunto:** Modelo Base e Regra de Negócio.
* **Mudança:** Versão inicial do script.
* **Funcionalidades:**
    1. Treinamento de dois modelos LightGBM (Grupo e Complexidade) com todos os dados históricos (2012+).
    2. Geração de predições em novos arquivos.
    3. Implementação de uma "camada de correção" (regra de negócio) para forçar a classificação "cirúrgico" em casos onde um código de cirurgia estava presente.