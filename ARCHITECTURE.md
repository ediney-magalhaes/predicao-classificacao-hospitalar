# Arquitetura do Sistema Preditivo - Classificação SUS

Este documento detalha o desenho arquitetural do pipeline de dados, a infraestrutura em nuvem, os protocolos de segurança e o ciclo de vida de Machine Learning (MLOps) aplicados no projeto.

Para decisões arquiteturais detalhadas, consulte as [ADRs](docs/adr/README.md).

---

## 1. Estrutura de Diretórios

```
sistema_classificacaoSUS_inteligente/
├── app.py                              # Entry point da GUI Streamlit
├── gerar_previsoes.py                  # Orquestrador de predições (sem I/O)
├── executar_treino.py                  # Pipeline de treinamento (consome Bronze do BigQuery)
├── config/
│   └── settings.py                     # Configurações centralizadas (Pydantic BaseSettings)
├── src/
│   ├── preprocessing/
│   │   └── preparo_ml.py              # Limpeza, feature engineering (dicionário CID)
│   ├── inference/
│   │   └── predicao.py                # Carregamento de modelos, predição, confiança, override
│   ├── validacao/
│   │   ├── validacao.py               # Schemas Pandera para validação das 3 planilhas de entrada
│   │   ├── schemas_pos_revisao.py     # Schemas Pandera pós-revisão + normalização case-insensitive
│   │   └── schemas_movimentacoes.py   # Schema Pandera do relatório de movimentações (4ª fonte)
│   ├── hitl/
│   │   ├── pipeline_correcao.py       # Orquestrador do ciclo HITL (validação -> comparação -> ingestão)
│   │   ├── comparador.py             # Cálculo pareado de diferenças original vs revisão
│   │   └── auditoria.py              # Registro de eventos HITL no BigQuery
│   └── ingestion/
│       ├── anonimizacao.py            # SHA-256 + salt para dados sensíveis
│       ├── carga_bq.py               # Ingestão na Bronze do BigQuery (idempotente por safra)
│       ├── preprocessamento_movimentacoes.py  # Reconstrução de layout bruto (colunas desconfiguradas)
│       └── ingestao_movimentacoes.py  # Orquestrador da 4ª fonte (validação -> anonimização -> ingestão)
├── scripts/
│   └── ingestao_historica.py          # Ingestão única do CSV consolidado 2012-2024
├── data/
│   └── Categorias de CIDs.xlsx        # Dicionário oficial CID-10 (referência fixa)
├── dbt_classificacao_analytics/       # Camada analítica dbt (Fase 3 — em construção)
│   └── models/
│       ├── staging/
│       │   ├── sources.yml            # Declaração das fontes Bronze (saídas + movimentações) e audit
│       │   ├── stg_bronze__saidas.sql # Tipagem de datas (3 formatos coexistentes)
│       │   └── stg_bronze__movimentacoes.sql  # Tipagem, combinação DATA+HORA
│       ├── intermediate/
│       │   ├── int_correcoes_hitl.sql          # Deduplicação de auditoria HITL por safra
│       │   └── int_movimentacoes_uti.sql       # Pareamento cronológico entrada/saída por unidade
│       └── marts/
│           ├── assistencial/
│           │   ├── mart_volume_assistencial.sql
│           │   └── mart_taxa_correcao.sql
│           ├── modelo/
│           │   └── mart_uti.sql       # teve_uti + dias_totais_uti por atendimento
│           └── financeiro/            # Parcialmente desbloqueado (ver amendment ADR-0004)
├── docs/
│   ├── adr/                           # Architecture Decision Records
│   ├── runbooks/                      # Procedimentos operacionais
│   └── model_cards/                   # Documentação por versão de modelo
├── .streamlit/
│   └── secrets.toml                   # Senha da GUI (não versionado)
├── .env                               # Salt, credenciais GCP (não versionado)
├── modelo_grupo_sus.joblib            # Modelo LightGBM — Grupo SUS
└── modelo_complexidade_sus.joblib     # Modelo LightGBM — Complexidade SUS
```

---

## 2. Visão Geral do Pipeline (End-to-End)

O sistema processa dados de internações hospitalares (on-premise), aplica modelos preditivos e retroalimenta um Data Warehouse na nuvem para consumo analítico. O fluxo opera em duas frentes: **Inferência Mensal** (via GUI) e **Retreinamento** (via terminal).

### 2.1. Fluxo de Inferência Mensal

```
Assistente acessa GUI (Streamlit)
        │
        ▼
Upload de 3 planilhas XLSX
(Saídas, Altas MV, Cirurgias)
        │
        ▼
Validação de schema (Pandera)
── rejeita com mensagem clara se inválido
        │
        ▼
Processamento (gerar_previsoes.py)
├── Deduplicação por ATENDIMENTO
├── Validação cruzada com altas do MV
│   (remove intrusos, alerta faltantes)
├── Merge com cirurgias (apenas principal)
├── Feature engineering (dicionário CID → Capítulo + Grupo)
        │
        ▼
Predição (src/inference/predicao.py)
├── LightGBM GRUPO_SUS + confiança (predict_proba)
├── LightGBM COMPLEXIDADE_SUS + confiança
├── Business Rule Override (cirurgia → cirúrgico)
        │
        ▼
Resultado na GUI
├── Alertas (duplicados, intrusos, faltantes)
├── Métricas (registros, overrides, baixa confiança)
├── Distribuição das predições
├── Download do XLSX com predições + confiança
```

**Princípio de design:** o orquestrador (`gerar_previsoes.py`) recebe DataFrames e devolve DataFrames — não faz I/O. Quem faz I/O é o "adapter" (GUI via `app.py`, ou terminal via `if __name__ == '__main__'`). Isso permite reusar a mesma lógica em qualquer contexto sem alteração.

### 2.2. Fluxo de Treinamento

```
Assistente baixa XLSX com predições
│
▼
Correção no Excel (~2h)
(altera PREVISAO_GRUPO e/ou PREVISAO_COMPLEXIDADE)
│
▼
Upload na GUI (aba "Enviar Correções")
├── Planilha revisada (correções HITL) — obrigatória
└── Relatório de movimentações (4ª fonte, UTI) — obrigatório, mesmo momento
│
▼
Validação pós-revisão (Pandera)
── normalização case-insensitive contra domínios SUS
── rejeita com mensagem clara se valor fora do domínio
│
▼
Localização da predição original na W:
(Banco Epidemio - Mês Ano - PREDICAO.xlsx)
│
▼
Comparação pareada (src/hitl/comparador.py)
├── Taxa de correção por variável-alvo
├── Detalhamento de transições (de → para, quantidade)
│
▼
Enriquecimento CID (merge com dicionário)
├── capitulo_breve, grupo_cid
│
▼
Anonimização (SHA-256 + salt)
│
▼
DELETE por safra_mes (idempotência)
│
▼
Append na Bronze (BigQuery)
│
▼
Registro de auditoria (audit.hitl_events)
│
▼
Resultado na GUI
├── Correções em Grupo / Complexidade / ambas
├── Taxa de correção por variável
├── Detalhamento das transições

```
**Princípio de design:** o orquestrador (`pipeline_correcao.py`) segue o mesmo padrão do `gerar_previsoes.py`, recebe DataFrames, devolve dicionário de resultado. O `app.py` é apenas adapter visual. Pipeline testável sem GUI.

### 2.3. Fluxo de Treinamento

1. **Extração:** `executar_treino.py` conecta à Camada Bronze do BigQuery.
2. **Filtro temporal:** Treina apenas com dados de 2020 em diante (combate a data drift histórico).
3. **Balanceamento:** `ImbPipeline` garante que SMOTE ocorra apenas nos dados de treino durante validação cruzada.
4. **Serialização:** Modelos salvos como `.joblib` na raiz do projeto.

---

## 3. Validação de Dados em Camadas (ADR-0001)

O projeto adota validação em três camadas, cada uma com a ferramenta adequada ao contexto:

| Camada | Ferramenta | O que valida | Quando executa |
|---|---|---|---|
| **Configs e objetos Python** | Pydantic v2 | Caminhos, features, thresholds, variáveis de ambiente | Na inicialização do sistema |
| **DataFrames de entrada** | Pandera | Schema das 3 planilhas (tipos, ranges, nulls, colunas obrigatórias) | No upload, antes de qualquer processamento |
| **Warehouse (Bronze→Silver→Gold)** | dbt tests + contracts | Integridade referencial, freshness, regras de negócio em SQL | Fase 3 (planejado) |

Detalhes completos em [ADR-0001](docs/adr/0001-validacao-de-dados-em-tres-camadas.md).

---

## 4. Configuração Centralizada (Pydantic BaseSettings)

Toda configuração do projeto é centralizada em `config/settings.py`:

- Caminhos de modelos e dados de referência
- Listas de features por modelo (na ordem do treino)
- Valores do Business Rule Override
- Colunas obrigatórias de cada planilha (consumidas pelo Pandera)
- Parâmetros da GUI

Variáveis sensíveis (`SALT_SUS`, credenciais GCP) são lidas automaticamente do `.env`. A validação ocorre na inicialização — se algo estiver faltando ou inválido, o sistema não sobe.

---

## 5. Interface da Assistente (GUI Streamlit)

**Decisão de hosting:** Streamlit roda localmente no PC do Ediney, acessível pela assistente via rede interna do hospital (`http://<IP>:8501`). Detalhes em [ADR-0002](docs/adr/0002-hosting-gui-streamlit-local.md).

**Por que local e não cloud:**
- Firewall hospitalar bloqueia domínios externos
- Dados de internação não devem transitar pela internet pública
- Zero dependência da TI para liberações
- Custo: R$ 0,00

**Estrutura da GUI:**
- Autenticação por senha (`st.secrets`)
- Duas abas: "Gerar Predições" e "Enviar Correções" (ambas operacionais)
- Upload de 3 planilhas com validação automática
- Resultado com alertas, métricas de confiança, distribuição e download

---

## 6. Arquitetura Medallion "Zero Cost" (Google BigQuery)

O sistema utiliza o Free Tier do Google Cloud (1 TB/mês de query, 10 GB storage) com abordagem Medallion.

### Estado atual:

- **🥉 Camada Bronze (Raw / Histórico Validado):** Duas tabelas físicas, únicas fontes de verdade cada uma no seu domínio. `bronze_saidas_anonimizado` (internações, 2012-2026, volume crescente com ~900 registros/mês via
append idempotente por safra). `bronze_movimentacoes_anonimizado` (relatório de movimentações internas, nova desde 2026-08-21, ~3.600 registros/mês). Ambas enriquecidas/anonimizadas antes da ingestão. Auditoria em tabela separada (`audit.hitl_events`). **Implementadas e em uso.**

- **🥈 Camada Silver (Standardized / Enriched):** View SQL lógica. Dois staging models: `stg_bronze__saidas` (tipagem completa de data/hora, 3 formatos coexistentes) e `stg_bronze__movimentacoes` (tipagem, combinação DATA+HORA). Duas intermediate: `int_correcoes_hitl` (deduplicação de auditoria) e `int_movimentacoes_uti` (pareamento cronológico de entrada/saída por unidade, cálculo de permanência).

- **🥇 Camada Gold (Aggregated / Business-Ready):** View SQL lógica. `marts_assistencial`: `mart_volume_assistencial` (grão=atendimento, enriquecido com faixa etária/convênio/unidade via seeds), `mart_taxa_correcao` (taxas por safra e versão do modelo). `marts_modelo`: `mart_uti` (teve_uti + dias_totais_uti por atendimento, consumido pelo Estudo 4 do ADR-0005). `marts_financeiro`: parcialmente desbloqueado (ver amendment ADR-0004), ainda não implementado.

### Princípio FinOps:
- Views em vez de tabelas materializadas em Silver/Gold (custo de storage zero)
- Particionamento por data + clustering por chaves de filtro frequente
- Modelos rodam localmente (CPU suficiente para LightGBM com ~900 linhas)
- Custo total mensal: R$ 0,00

---

## 7. Ciclo de Vida MLOps

### 7.1. Inferência com Confiança
Cada predição acompanha um score de confiança (`max(predict_proba)`). Valores abaixo de 0.7 são sinalizados como "baixa confiança" na GUI, orientando a assistente a revisar com atenção.

**Nota:** as probabilidades ainda não estão calibradas (Fase 6, ADR-0009). O score atual indica confiança relativa, não probabilidade real.

### 7.2. Business Rule Override
Trava de segurança que corrige predições onde o modelo disse "Procedimentos clínicos" mas o paciente possui registro de cirurgia realizada. Valores e classes configuráveis via `settings.py`.

### 7.3. Human-in-the-Loop
A IA atua como sistema de suporte à decisão. A assistente revisa as predições, corrige erros e reenvia a planilha corrigida pela GUI. O sistema detecta diferenças (taxa de correção por variável-alvo com detalhamento de transições), anonimiza e alimenta a Bronze para retreino. Cada evento é registrado na tabela de auditoria com revisor, timestamp e métricas.

### 7.4. Cache de Modelos
Os modelos LightGBM são carregados uma vez e cacheados em memória (`src/inference/predicao.py`). Chamadas subsequentes reutilizam o cache sem recarregar do disco.

### 7.5. Evolução Planejada (Roadmap)
- **Fase 2:** Ciclo HITL automatizado ✅ (upload de correções, comparação, auditoria, ingestão histórica na Bronze)
- **Fase 3:** Silver/Gold em dbt, dashboard BI
- **Fase 4:** Monitoramento de drift (PSI, performance ao longo do tempo)
- **Fase 5:** Continuous Training com champion vs challenger
- **Fase 6:** Explicabilidade (SHAP) e calibração de probabilidades
- **Fase 7:** Active Learning (priorização de revisão por incerteza)
- **Fase 8:** Containerização Docker, testes, documentação completa

---

## 8. Segurança, Privacidade e LGPD

Tratando-se de dados sensíveis de saúde (PHI), a arquitetura incorpora proteção por padrão (Privacy by Design):

1. **Anonimização Criptográfica:** Nomes e CPFs nunca são enviados à nuvem em texto plano. O pipeline local aplica hashing irreversível SHA-256 combinado com salt criptográfico aleatório (injetado via `.env`).
2. **Gerenciamento de Segredos:** Salt, credenciais GCP e senha da GUI são gerenciados via `.env` e `.streamlit/secrets.toml`, ambos excluídos do versionamento.
3. **Autenticação Cloud:** Acesso ao BigQuery via Service Accounts do GCP com privilégio mínimo (IAM).
4. **Dados na rede interna:** A GUI roda na LAN do hospital — dados de internação nunca transitam pela internet pública.

---

## 9. Stack Tecnológica

| Categoria | Tecnologias |
|---|---|
| **Core** | Python 3.12, Pandas, Scikit-Learn |
| **Machine Learning** | LightGBM, Imbalanced-Learn (SMOTE) |
| **Configuração** | Pydantic v2 (BaseSettings), python-dotenv |
| **Validação de dados** | Pandera (DataFrames), dbt tests (warehouse, planejado) |
| **Interface** | Streamlit (GUI local na rede hospitalar) |
| **Data Warehouse** | Google BigQuery Free Tier (Standard SQL) |
| **Versionamento** | Git, GitHub |
| **Governança** | ADRs (MADR), Model Cards, Runbooks |