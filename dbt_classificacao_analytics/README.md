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
| `marts_financeiro` | Parcialmente desbloqueado — ver amendment ADR-0004 |

## Fonte de dados

Declaradas em [`models/staging/sources.yml`](models/staging/sources.yml):

- `bronze_saidas_anonimizado` internações, dataset `dados_saidas_hospitalares`,
  54 colunas, histórico 2012–2026
- `bronze_movimentacoes_anonimizado`, relatório de movimentações internas
  (nova, 2026-08-21), mesmo dataset, usada para reconstruir passagem por UTI
- `audit.hitl_events` — auditoria do ciclo HITL

## Models existentes

### `staging/`

- **`stg_bronze__saidas.sql`** tipagem de data/hora (3 formatos
  coexistentes: brasileiro, ISO, serial Excel) + demais 46 colunas
  geradas via `dbt-codegen`. Completo.
- **`stg_bronze__movimentacoes.sql`** — tipagem, combina `DATA`+`HORA` em
  timestamp único via `SAFE.PARSE_DATETIME` (formato único confirmado,
  `YYYY-MM-DD`)

### `intermediate/`

- **`int_correcoes_hitl.sql`** deduplicação de eventos de auditoria por
  `safra_mes` (residem duplicatas de teste; `MAX(data_revisao)` resolve)
- **`int_movimentacoes_uti.sql`** pareamento cronológico de entrada/saída
  por unidade a partir do relatório de movimentações. Classifica cada
  evento como `entrada` (INTERNACAO, TRANSFER. DE) ou `saida` (TRANSFER.
  PARA, ALTA), usa `LEAD()` para calcular a duração em cada unidade, com
  critério de desempate para eventos no mesmo timestamp (a mesma
  transferência vista dos dois lados). Grão: 1 linha por estadia em unidade.

### `marts/assistencial/`

- **`mart_volume_assistencial.sql`** grão=atendimento, enriquecido com
  faixa etária, convênio agrupado e unidade agrupada via seeds
- **`mart_taxa_correcao.sql`** taxas de correção por safra e versão do
  modelo

### `marts/modelo/`

- **`mart_uti.sql`** grão=atendimento, agrega `int_movimentacoes_uti`
  em `teve_uti` + `dias_totais_uti` + `qtd_passagens_uti`. Vive aqui (não
  em `assistencial`) porque seu consumo real é o Estudo 4 do ADR-0005
  (correlação UTI×complexidade), não uma métrica assistencial de rotina

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

- [ ] dbt contracts ativos nos modelos críticos
- [ ] `marts_financeiro/` parcialmente desbloqueado (2026-08-21, amendment
      ADR-0004). Estudos 1 e 2 (dependentes de valor) têm nova fonte
      candidata (relatório "HSR - Análise de Contas"), pendente validação
      contra nota fiscal real antes de implementar
- [ ] `mart_desempenho_modelo` desbloqueado (2026-08-21, previsao_grupo/
      previsao_complexidade disponíveis na Bronze), ainda não iniciado
- [ ] "Top 5 transições de erro" em `mart_taxa_correcao` — desbloqueado,
      ainda não implementado
- [ ] Reingestão histórica 2014-2019
- [ ] Deprecation warning em testes `accepted_values` (top-level arguments
      deprecados, precisam migrar para `arguments:` em versão futura do dbt)