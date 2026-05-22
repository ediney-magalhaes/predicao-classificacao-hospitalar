# Fase 2 — Ciclo HITL Automatizado: Desenho Técnico

## Visão Geral

Fechar o loop assistente → BigQuery sem intervenção manual do Ediney.

## Fluxo Completo

```
┌─────────────────────────────────────────────────────────────────────┐
│ FASE 1 (já funciona)                                                │
│                                                                     │
│  Assistente abre GUI → upload 3 planilhas → modelo gera predições   │
│  → download XLSX com PREVISAO_GRUPO + PREVISAO_COMPLEXIDADE         │
│                                                                     │
│  App salva cópia da predição original na W: automaticamente         │
│  (previsoes_original_YYYYMM.xlsx)                                   │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│ INTERVALO (~2 horas)                                                │
│                                                                     │
│  Assistente abre XLSX no Excel                                      │
│  Corrige PREVISAO_GRUPO e PREVISAO_COMPLEXIDADE onde necessário     │
│  Salva na W: (previsoes_revisada_YYYYMM.xlsx)                       │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│ FASE 2 (construir)                                                  │
│                                                                     │
│  Assistente volta na GUI → aba "Enviar Correções"                   │
│  Upload da planilha revisada                                        │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ 1. VALIDAÇÃO DE ENTRADA (Pandera)                           │    │
│  │    - Schema da planilha revisada                             │    │
│  │    - Colunas obrigatórias presentes                          │    │
│  │    - Valores de PREVISAO_GRUPO e PREVISAO_COMPLEXIDADE       │    │
│  │      dentro dos domínios válidos                             │    │
│  │    - Se inválida: mensagem clara, bloqueia pipeline          │    │
│  └──────────────────────────┬──────────────────────────────────┘    │
│                              │                                      │
│                              ▼                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ 2. PAREAMENTO E DETECÇÃO DE DIFERENÇAS                      │    │
│  │    - Carrega predição original da W: (mesmo mês/ano)         │    │
│  │    - Join por chave de atendimento                           │    │
│  │    - Compara PREVISAO_GRUPO e PREVISAO_COMPLEXIDADE          │    │
│  │    - Calcula:                                                │    │
│  │      · total_registros                                       │    │
│  │      · correcoes_grupo (count + %)                           │    │
│  │      · correcoes_complexidade (count + %)                    │    │
│  │      · correcoes_ambos (count + %)                           │    │
│  │      · detalhamento por classe (de X → para Y)               │    │
│  │    - Exibe resumo na GUI antes de confirmar                  │    │
│  └──────────────────────────┬──────────────────────────────────┘    │
│                              │                                      │
│                              ▼                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ 3. CONFIRMAÇÃO DA ASSISTENTE                                │    │
│  │    - GUI mostra resumo: "X correções em Grupo, Y em         │    │
│  │      Complexidade. Confirma envio?"                          │    │
│  │    - Botão de confirmação                                    │    │
│  └──────────────────────────┬──────────────────────────────────┘    │
│                              │                                      │
│                              ▼                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ 4. ANONIMIZAÇÃO                                             │    │
│  │    - SHA-256 + salt (src/ingestion/anonimizacao.py)          │    │
│  │    - Remove colunas sensíveis (nome, CPF, endereço, etc.)   │    │
│  │    - Padroniza nomes de colunas                              │    │
│  └──────────────────────────┬──────────────────────────────────┘    │
│                              │                                      │
│                              ▼                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ 5. VALIDAÇÃO PRÉ-ESCRITA (Pandera)                          │    │
│  │    - Schema do DataFrame anonimizado antes de ir pro BQ      │    │
│  │    - Garante que anonimização não corrompeu dados            │    │
│  │    - Tipos, nulls, domínios pós-anonimização                 │    │
│  └──────────────────────────┬──────────────────────────────────┘    │
│                              │                                      │
│                              ▼                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ 6. APPEND NA BRONZE (BigQuery)                              │    │
│  │    - src/ingestion/carga_bq.py (corrigido: append, não      │    │
│  │      replace)                                                │    │
│  │    - Credenciais passadas corretamente                       │    │
│  │    - Coluna safra_mes (YYYY-MM) adicionada                  │    │
│  │    - Coluna data_ingestao (timestamp)                        │    │
│  └──────────────────────────┬──────────────────────────────────┘    │
│                              │                                      │
│                              ▼                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ 7. REGISTRO DE AUDITORIA (BigQuery: audit.hitl_events)      │    │
│  │    - safra_mes                                               │    │
│  │    - data_revisao (timestamp)                                │    │
│  │    - revisor ("assistente" — campo texto, não PII)           │    │
│  │    - hash_arquivo_original (SHA-256 do XLSX original)        │    │
│  │    - hash_arquivo_revisado (SHA-256 do XLSX revisado)        │    │
│  │    - total_registros                                         │    │
│  │    - correcoes_grupo                                         │    │
│  │    - correcoes_complexidade                                  │    │
│  │    - correcoes_ambos                                         │    │
│  │    - tempo_revisao_minutos (estimado: diff entre download    │    │
│  │      da predição e upload da correção)                       │    │
│  │    - versao_modelo (qual .joblib foi usado)                  │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                     │
│  GUI exibe: "✅ Correções processadas. X registros anonimizados     │
│  enviados para a base de treino. Auditoria registrada."             │
└─────────────────────────────────────────────────────────────────────┘
```

## Alterações Técnicas Necessárias

### Arquivos a CRIAR

| Arquivo | Responsabilidade |
|---|---|
| `src/hitl/comparador.py` | Pareia original vs revisada, calcula métricas de correção |
| `src/hitl/auditoria.py` | Monta registro de auditoria e envia pro BigQuery |
| `src/hitl/__init__.py` | Package init |
| `src/validacao/schemas_ingestao.py` | Schemas Pandera para validação pré-escrita na Bronze |

### Arquivos a REFATORAR

| Arquivo | O que muda |
|---|---|
| `src/ingestion/carga_bq.py` | `if_exists='replace'` → `'append'`; passar credenciais; adicionar colunas `safra_mes` e `data_ingestao` |
| `src/ingestion/anonimizacao.py` | Garantir idempotência (se rodar 2x no mesmo dado, não quebra); adicionar validação de colunas esperadas antes de dropar |
| `app.py` | Aba "Enviar Correções": upload da revisada, exibir diff, confirmação, trigger do pipeline |
| `config/settings.py` | Adicionar: `W_DRIVE_PATH`, `BRONZE_TABLE`, `AUDIT_TABLE`, `MODEL_VERSION` |

### Tabelas BigQuery a CRIAR

| Tabela | Schema resumido |
|---|---|
| `audit.hitl_events` | safra_mes, data_revisao, revisor, hash_original, hash_revisado, total_registros, correcoes_grupo, correcoes_complexidade, correcoes_ambos, tempo_revisao_min, versao_modelo |

### Tabela BigQuery a ALTERAR

| Tabela | O que muda |
|---|---|
| `dados_saidas_hospitalares.saidas_anonimizadas` (Bronze) | Adicionar colunas `safra_mes` (STRING, formato YYYY-MM) e `data_ingestao` (TIMESTAMP) para permitir append incremental e rastreabilidade |

## Ordem de Implementação Sugerida

1. **Settings** — adicionar configs novas no Pydantic BaseSettings
2. **Corrigir carga_bq.py** — fix crítico (replace → append + credenciais)
3. **schemas_ingestao.py** — schemas Pandera de validação pré-escrita
4. **anonimizacao.py** — refatorar pra ser defensivo
5. **comparador.py** — lógica de diff entre original e revisada
6. **auditoria.py** — registro de auditoria no BigQuery
7. **app.py** — integrar tudo na aba "Enviar Correções"
8. **Teste end-to-end** — fluxo completo com dados reais

## Pré-requisitos

- [ ] ADR-0003 fechada (este documento)
- [ ] Credenciais GCP configuradas no `.env` do ambiente de execução
- [ ] Pasta W: acessível do ambiente onde o app roda
- [ ] Dataset `audit` criado no BigQuery (uma vez, manualmente)