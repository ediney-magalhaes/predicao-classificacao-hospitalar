# Histórico de Alterações (Changelog) - Projeto Classificação SUS

Este documento registra as principais mudanças no sistema de classificação.

O projeto adota **Versionamento Semântico (SemVer)**: `MAJOR.MINOR.PATCH`
- **MAJOR:** mudança que quebra compatibilidade (nova arquitetura, mudança de interface)
- **MINOR:** funcionalidade nova sem quebra de compatibilidade
- **PATCH:** correção de bug ou ajuste menor

---

## Em andamento — Fase 3 (Camada Analítica em dbt)

* **Assunto:** Estrutura inicial do projeto dbt e primeiro model de staging.
* **Status:** Parcial — não consolidado em versão até o fechamento dos critérios de pronto da Fase 3.
* **Ações realizadas até aqui:**
    1. **Setup dbt Core:** `dbt init`, `profiles.yml` configurado com service account, `dbt debug` validado contra `ml-classificacao-sus`.
    2. **ADR-0004 fechada:** estratégia de Views por camada (staging/intermediate/marts), datasets separados no BigQuery.
    3. **Amendment ADR-0004:** `marts_financeiro` suspenso — colunas `vl_conta`/`vl_honorario` excluídas da ingestão Bronze por falta de validação de integridade.
    4. **`sources.yml`:** fonte `bronze_saidas_anonimizado` declarada (54 colunas, dataset `dados_saidas_hospitalares`).
    5. **`stg_bronze__saidas.sql` (parcial):** tipagem de 6 colunas de data/hora. Tratamento de 3 formatos coexistentes na Bronze histórica (brasileiro, ISO, número serial do Excel) via `COALESCE` + `SAFE.PARSE_DATE`/`PARSE_DATETIME`. Combinação de `dt_alta` + `hr_alta` em datetime único.
* **Pendências:**
    - [ ] Adicionar as demais 48 colunas (não-data) ao `stg_bronze__saidas.sql`
    - [ ] Models de `intermediate/` e `marts/{assistencial,modelo}/`
    - [ ] dbt tests e contracts
    - [ ] dbt docs gerado

---

## v6.0.0 (Maio de 2026)
* **Assunto:** Ciclo HITL Automatizado + Ingestão Histórica na Bronze.
* **Mudança:** Implementação completa da Fase 2 — a assistente agora envia correções pela GUI, o sistema detecta diferenças, anonimiza e ingere na Bronze do BigQuery automaticamente. Bronze recriada do zero com 110.136 registros (2012-2026).
* **Motivo:** Após a Fase 1, a planilha corrigida morria no PC da assistente. Sem ela de volta no pipeline, não havia como medir taxa de correção, alimentar a Bronze com labels confiáveis para retreino, nem auditar quem revisou o quê.
* **Ações:**
    1. **Pipeline de correção:** `src/hitl/pipeline_correcao.py` orquestra o fluxo completo pós-revisão: validação (Pandera) -> localização da predição original na W: -> comparação pareada -> enriquecimento CID -> anonimização (SHA-256 + salt) -> append na Bronze -> registro de auditoria.
    2. **Comparador:** `src/hitl/comparador.py` calcula diferenças entre predição original e revisão humana. Métricas: taxa de correção por variável-alvo, detalhamento das transições (ex: "Procedimentos cirúrgicos -> Procedimentos clínicos: 101 ocorrências").
    3. **Auditoria:** `src/hitl/auditoria.py` registra cada evento HITL no BigQuery (`audit.hitl_events`) com revisor, timestamp, hash do arquivo, safra e métricas de correção.
    4. **Validação pós-revisão:** `src/validacao/schemas_pos_revisao.py` com normalização case-insensitive dos valores digitados pela assistente contra domínios oficiais do SUS (carregados do dicionário de classificação).
    5. **Enriquecimento CID:** `engenharia_features` integrado ao pipeline de correção — merge com dicionário CID traz `capitulo_breve` e `grupo_cid` para a Bronze via coluna auxiliar (preserva `cid_1_principal` original com código + descrição).
    6. **Deduplicação por safra:** `carga_bq.py` executa DELETE por `safra_mes` antes do append, garantindo idempotência — reprocessar um mês não duplica dados.
    7. **Atendimentos faltantes:** GUI exibe números de atendimento que constam no MV mas não na planilha epidemio, para a assistente buscar no sistema hospitalar.
    8. **Ingestão histórica:** `scripts/ingestao_historica.py` processou o CSV consolidado (2012-2024): 109.333 registros em 150 safras, com enriquecimento CID e anonimização. Idempotente via deduplicação por safra.
    9. **Correção de bug crítico:** `carga_bq.py` usava `if_exists='replace'` — Bronze ficou estática desde fevereiro de 2026. Corrigido para `append` com deduplicação.
* **ADR fechada:** ADR-0003 (storage de planilhas na W: com pipeline de ingestão anonimizada para BigQuery).
* **Bronze:** 110.136 registros totais (109.333 históricos + 803 de abril/2026). Schema com 54 colunas incluindo `capitulo_breve`, `grupo_cid`, `safra_mes` e `data_ingestao`.
* **Métricas de baseline (abril/2026):** Taxa de correção Grupo: 13.3% (107/803). Taxa de correção Complexidade: 0.0%. Transição dominante: "Procedimentos cirúrgicos -> Procedimentos clínicos" (101 de 107 correções).
* **Resultado:** Ciclo HITL fechado — assistente gera predições, corrige no Excel, envia correções pela GUI, sistema compara, anonimiza e ingere na Bronze sem intervenção do Ediney. Pipeline pronto para alimentar Continuous Training na Fase 5.

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