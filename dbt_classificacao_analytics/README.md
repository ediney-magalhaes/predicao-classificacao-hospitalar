# Camada Analítica — dbt Core (Fase 3)

Projeto dbt responsável pela camada analítica do Sistema Preditivo de Classificação SUS, transformando os dados da Bronze (BigQuery) em Views consumíveis por dashboards executivos (Power BI).

Decisão arquitetural completa em [`docs/adr/0004-estrategia-dbt-silver-gold.md`](../docs/adr/0004-estrategia-dbt-silver-gold.md).

---

## Arquitetura
```
staging/ → intermediate/ → marts/{assistencial, modelo, financeiro}
```
Todas as camadas materializadas como **Views** (custo zero, volume atual de ~900 registros/mês não justifica tabelas físicas).

| Dataset BigQuery | Conteúdo |
|---|---|
| `dados_saidas_hospitalares` | Bronze (fonte, tabela física) |
| `staging` | Models de staging |
| `intermediate` | Lógica compartilhada entre marts |
| `marts_assistencial` | Perfil de pacientes, volumetria |
| `marts_modelo` | Desempenho do modelo, taxa de correção |
| `marts_financeiro` | Suspenso — ver amendment ADR-0004 |

## Fonte de dados

Declarada em [`models/staging/sources.yml`](models/staging/sources.yml): tabela `bronze_saidas_anonimizado`, dataset `dados_saidas_hospitalares`, 54 colunas, ~110k registros históricos (2012–2026).

## Models existentes

### `staging/stg_bronze__saidas.sql`

Tipagem das colunas de data/hora da Bronze. Status: **parcial** — trata apenas as 6 colunas de data; as demais 48 colunas da Bronze ainda não estão incluídas (pendência registrada).

**Por que essa lógica é mais complexa que um cast simples:** a Bronze acumula 5 anos de exportações de fontes diferentes, e os campos de data coexistem em **3 formatos distintos** na mesma coluna:

1. Brasileiro — `DD/MM/YYYY` (ou com hora, `DD/MM/YYYY HH:MM[:SS]`)
2. ISO — `YYYY-MM-DD` (ou com hora, `YYYY-MM-DD HH:MM:SS`)
3. Número serial do Excel — ex. `"45173,40162"` (dias desde `1899-12-30`, parte fracionária = hora do dia), presente em registros históricos de 2023 na coluna `dtsumario`

A estratégia usa `COALESCE` + `SAFE.PARSE_DATE`/`SAFE.PARSE_DATETIME` para tentar cada formato em sequência sem quebrar a query (`SAFE.` retorna `NULL` em vez de erro fatal quando o formato não bate). O terceiro formato (Excel) usa `DATETIME_ADD` encadeado, somando dias e depois segundos a partir da data-base `1899-12-30`.

Colunas com hora e data separadas na origem (`dt_alta` + `hr_alta`) são combinadas via `CONCAT` + `LPAD` (padroniza hora pra sempre 2 dígitos) antes do parsing.

## Convenções de nomenclatura

| Camada | Prefixo | Exemplo |
|---|---|---|
| Staging | `stg_<source>__<entity>` | `stg_bronze__saidas` |
| Intermediate | `int_<descricao>` | `int_correcoes_modelo` |
| Marts | `mart_<dominio>_<descricao>` | `mart_desempenho_modelo` |

## Como rodar

```bash
cd dbt_classificacao_analytics
dbt debug                                    # valida conexão com BigQuery
dbt parse                                    # valida sintaxe de todos os models
dbt run --select stg_bronze__saidas          # roda um model específico
dbt run                                      # roda todos os models
dbt show --select stg_bronze__saidas --limit 50   # preview de resultado sem abrir BigQuery
```

`profiles.yml` (credenciais) fica fora deste repositório, em `~/.dbt/profiles.yml` — precisa ser recriado em qualquer outra máquina via `dbt init`.

## Pendências conhecidas

- [ ] `stg_bronze__saidas.sql` incompleto — faltam 48 colunas não-data
- [ ] `marts_financeiro/` é placeholder — suspenso por falta de validação de `vl_conta`/`vl_honorario` (ADR-0004, amendment)
- [ ] Warning de `dbt parse`/`dbt run` sobre `intermediate`/`marts` sem resources é esperado até que existam models nessas pastas