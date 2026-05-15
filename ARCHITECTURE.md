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
│   │   └── validacao.py               # Schemas Pandera para validação das 3 planilhas
│   └── ingestion/
│       ├── anonimizacao.py            # SHA-256 + salt para dados sensíveis
│       └── carga_bq.py               # Ingestão na Bronze do BigQuery
├── data/
│   └── Categorias de CIDs.xlsx        # Dicionário oficial CID-10 (referência fixa)
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
- Duas abas: "Gerar Predições" (ativa) e "Enviar Correções" (Fase 2, placeholder)
- Upload de 3 planilhas com validação automática
- Resultado com alertas, métricas de confiança, distribuição e download

---

## 6. Arquitetura Medallion "Zero Cost" (Google BigQuery)

O sistema utiliza o Free Tier do Google Cloud (1 TB/mês de query, 10 GB storage) com abordagem Medallion.

### Estado atual:

- **🥉 Camada Bronze (Raw / Histórico Validado):** Tabela física. Única fonte de verdade. Recebe dados via append mensal após validação humana. **Implementada e em uso.**

- **🥈 Camada Silver (Standardized / Enriched):** View SQL lógica. Limpeza padronizada (tipagem, nulls, nomenclatura). **Planejada para Fase 3.**

- **🥇 Camada Gold (Aggregated / Business-Ready):** View SQL lógica. Agregações para consumo do BI (volumetria, performance, taxa de correção). **Planejada para Fase 3.**

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
A IA atua como sistema de suporte à decisão. A assistente revisa as predições, corrige erros e futuramente (Fase 2) reenvia a planilha corrigida ao sistema, que detecta diferenças e alimenta a Bronze para retreino.

### 7.4. Cache de Modelos
Os modelos LightGBM são carregados uma vez e cacheados em memória (`src/inference/predicao.py`). Chamadas subsequentes reutilizam o cache sem recarregar do disco.

### 7.5. Evolução Planejada (Roadmap)
- **Fase 2:** Ciclo HITL automatizado (upload de correções, auditoria, ingestão na Bronze)
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