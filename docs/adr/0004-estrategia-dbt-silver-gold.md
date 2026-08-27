# ADR-0004 — Estratégia dbt: Camadas Silver/Gold no BigQuery

**Status:** Aceita  
**Data:** 2026-05-28  
**Autor:** Ediney Magalhães  
**Contexto da fase:** Fase 3 — Camada Analítica + BI

---

## Log de Atualizações

| Data | Resumo |
|---|---|
| 2026-06-25 | `marts_financeiro` suspensa — `vl_conta`/`vl_honorario` não validados |
| 2026-07-28 | Escopo de `marts_assistencial` unificado em 1 model (⚠️ aplicado inline na seção "Escopo dos Marts", exceção ao padrão de log anexado — mantido por respeito ao registro histórico já feito) |
| 2026-08-21 | 4 de 5 estudos financeiros desbloqueados — nova fonte identificada (relatório Qlik "HSR - Análise de Contas") |
| 2026-08-26 | Fonte financeira validada contra sistema MV — regra de agregação definida e testada, Estudos 1 e 2 destravados |

---

## Y-Statement

**Para** a equipe de gestão hospitalar e o engenheiro responsável pelo modelo,  
**que precisam de** indicadores assistenciais, perfil de pacientes, desempenho do modelo e análise financeira exploratória,
**o** projeto adota dbt Core com materialização em Views no BigQuery, organizado em camadas `staging → intermediate → marts` com datasets separados por camada,  
**para conseguir** governança analítica com custo zero, lineage navegável e separação clara de audiências,  
**aceitando que** a orquestração automática (scheduler) será resolvida na Fase 5 via GitHub Actions, e que as Views exigem reprocessamento da Bronze a cada query (aceitável dado o volume).

---

## Contexto

A Bronze contém 110.136 registros (2012–2026) com schema de 54 colunas, crescendo ~900 registros/mês via pipeline HITL. Os dados incluem predições originais do modelo (`previsao_grupo`, `previsao_complexidade`), rótulos corrigidos pela assistente (`grupo_sus`, `complexidade_sus`), metadados financeiros (`vl_conta`, `vl_honorario`), clínicos (`nr_dias`, `entrada_uti`, `cid_1_principal`) e demográficos (`idade`, `sexo`, `municipio`).

Hoje não existe nenhuma camada analítica. O Power BI apontaria diretamente para a Bronze — 54 colunas cruas, sem tipagem consistente, com nomes de colunas técnicos e sem agregações de negócio.

**Problemas que essa ADR resolve:**

- Gestores e diretores não conseguem consumir a Bronze diretamente no Power BI sem tratamento
- Não há separação entre métricas técnicas (para o engenheiro) e métricas de negócio (para gestão)
- Sem camada intermediária, qualquer mudança no schema da Bronze quebra os relatórios do Power BI
- Não há lineage documentado das transformações aplicadas aos dados

---

## Decision Drivers

1. **Custo zero inegociável** — free tier do BigQuery: 10 GB storage, 1 TB query/mês
2. **Volume baixo** — 110k registros, crescimento de ~900/mês, 5–10 queries/mês no Power BI
3. **Time de um** — complexidade operacional deve ser mínima
4. **dbt como diferencial técnico** — Este projeto aprofunda o padrão `staging → intermediate → marts`
5. **Separação de audiências** — engenheiro precisa de métricas técnicas; gestores precisam de indicadores de negócio
6. **Manutenibilidade** — mudanças no schema da Bronze não devem exigir reescrita dos relatórios Power BI

---

## Opções Consideradas

### Opção A — Views SQL nativas no BigQuery (sem dbt)
Criar as Views diretamente no console do BigQuery, sem framework.

**Prós:** zero dependência, setup em minutos  
**Contras:** sem lineage, sem testes, sem documentação automática, não escala, não aparece em currículo

### Opção B — dbt Core local com Views *(escolhida)*
dbt Core instalado localmente, rodando `dbt run` manualmente após cada ingestão HITL. Toda a camada analítica como Views no BigQuery.

**Prós:** lineage navegável (`dbt docs`), testes nativos (`not_null`, `unique`, `accepted_values`), contratos de schema, padrão de mercado, custo zero, documentação automática  
**Contras:** sem scheduler automático até a Fase 5; requer `dbt run` manual após cada safra

### Opção C — dbt Cloud free tier
dbt Cloud com scheduler integrado e UI de lineage hospedada.

**Prós:** scheduler visual, UI de DAG pronta para portfólio  
**Contras:** free tier limita a 1 projeto por conta; conta corporativa já ocupa essa vaga. Conta pessoal separada é possível, mas cria fragmentação. Scheduler será resolvido via GitHub Actions na Fase 5 de qualquer forma.

### Opção D — Tabelas materializadas em vez de Views
Criar tabelas físicas nas camadas Silver/Gold para performance.

**Prós:** queries mais rápidas, não reprocessa Bronze a cada acesso  
**Contras:** custo de storage (mesmo que baixo), complexidade de refresh, desnecessário para 110k registros e 5–10 queries/mês. Revisitar se Power BI reportar lentidão.

---

## Decisão

**dbt Core local, todas as camadas como Views, datasets separados por camada no BigQuery.**

### Estrutura de datasets no BigQuery

| Dataset BigQuery | Conteúdo | Quem acessa |
|---|---|---|
| `dados_saidas_hospitalares` | Bronze (tabela física existente) | Pipeline Python, dbt (source) |
| `staging` | Models de staging | dbt interno, nunca Power BI |
| `intermediate` | Lógica compartilhada entre marts | dbt interno, nunca Power BI |
| `marts_assistencial` | Perfil de pacientes, volumetria | Power BI — gestores e diretores |
| `marts_modelo` | Desempenho do modelo, taxa de correção | Power BI — engenheiro |
| `marts_financeiro` | Análise exploratória financeira | Power BI — gestores e diretores |

### Estrutura do projeto dbt

```
dbt_sus/
├── dbt_project.yml
├── profiles.yml              ← aponta pro BigQuery via service account
├── models/
│   ├── staging/
│   │   └── stg_bronze__saidas.sql
│   ├── intermediate/
│   │   ├── int_saidas_enriquecidas.sql
│   │   └── int_correcoes_modelo.sql
│   └── marts/
│       ├── assistencial/
│       │   ├── mart_perfil_paciente.sql
│       │   └── mart_volume_assistencial.sql
│       ├── modelo/
│       │   ├── mart_desempenho_modelo.sql
│       │   └── mart_taxa_correcao.sql
│       └── financeiro/
│           └── mart_analise_financeira.sql
├── tests/
├── macros/
└── docs/
```

### Convenções de nomenclatura

| Camada | Prefixo | Exemplo |
|---|---|---|
| Staging | `stg_<source>__<entity>` | `stg_bronze__saidas` |
| Intermediate | `int_<descricao>` | `int_correcoes_modelo` |
| Marts | `mart_<dominio>_<descricao>` | `mart_desempenho_modelo` |

Duplo underscore (`__`) entre source e entidade no staging é convenção oficial dbt que separa visualmente a origem da entidade.

### Materialização

Todas as camadas como **Views** (`materialized='view'` no `dbt_project.yml`).

Revisitar para `table` se: Power BI reportar tempo de atualização > 30 segundos, ou volume da Bronze ultrapassar 1 milhão de registros.

---

## Escopo dos Marts

### `marts_assistencial`

**mart_perfil_paciente** — uma linha por safra com distribuições demográficas:
- Distribuição por faixa etária (agrupamento de `idade`)
- Distribuição por sexo
- Top 10 municípios de origem
- Distribuição por tipo de internação
- Taxa de internação em UTI (`entrada_uti`)
- Média de dias de internação (`nr_dias`) por grupo e complexidade

**mart_volume_assistencial** — volumetria mensal:
- Total de saídas por safra
- Distribuição de `grupo_sus` e `complexidade_sus` (rótulos corrigidos)
- Top 10 CIDs principais (`cid_1_principal`)
- Sazonalidade mensal e anual

## Atualização — 2026-07-28

**Escopo de marts_assistencial revisado:** a seção original previa dois models 
(mart_perfil_paciente e mart_volume_assistencial). Na implementação, optou-se por 
um único model (mart_volume_assistencial), grão de 1 linha por atendimento, cobrindo 
todas as dimensões de ambos os escopos originais (sexo, faixa etária, UTI quando 
disponível, dias de internação, município, CID, volumetria). Motivo: grão de 
atendimento já permite qualquer agregação que os dois marts separados ofereceriam, 
sem duplicação de base. mart_perfil_paciente não será implementado como model 
separado, salvo necessidade futura identificada pelos estudos estatísticos (ADR-0005).

### `marts_modelo`

**mart_desempenho_modelo** — métricas de performance por safra:
- Total de predições por safra
- Acertos e erros por classe (grupo e complexidade)
- Precision e Recall aproximados por classe (calculáveis em SQL com contagem de TP/FP/FN)
- Versão do modelo usada na safra

**mart_taxa_correcao** — análise do loop HITL:
- Taxa de correção de grupo por safra (% de registros alterados)
- Taxa de correção de complexidade por safra
- Top 5 transições de erro mais frequentes (ex: "Clínico → Cirúrgico")
- Tendência: taxa de correção deveria cair ao longo do tempo conforme modelo retreina

### `marts_financeiro`

Análise exploratória com `vl_conta`, `vl_honorario`, `nr_dias`. Sem estimativa de glosas (tabelas de convênios indisponíveis).

**Estudos implementados no mart:**

1. **Dispersão valor da conta × complexidade/grupo** — base para gráfico de dispersão no Power BI. Identifica se erros de classificação concentram em internações de maior valor (risco financeiro).

2. **Distribuição de `vl_conta` por classe predita vs corrigida** — evidencia se correções humanas têm viés financeiro (o modelo erra mais em internações caras?).

3. **`nr_dias` médio por grupo e complexidade** — proxy de consumo de recursos. Inconsistências entre dias de internação e complexidade classificada são sinais de erro histórico.

4. **Correlação UTI × complexidade** — proporção de internações com `entrada_uti = S` por classe de complexidade. Alta complexidade sem UTI ou UTI sem alta complexidade são anomalias que merecem investigação.

5. **Sazonalidade de volume e valor médio** — `vl_conta` médio e total por mês/ano. Útil para planejamento de capacidade e identificação de outliers sazonais.

---

## Consequências

**Positivas:**
- Lineage completo navegável via `dbt docs serve`
- Testes de qualidade aplicados antes de qualquer dado chegar ao Power BI
- Mudanças no schema da Bronze são absorvidas na camada de staging, sem impacto nos relatórios
- Padrão de mercado documentável em currículo e entrevistas

**Negativas / Trade-offs aceitos:**
- `dbt run` precisa ser executado manualmente após cada ingestão HITL até a Fase 5
- Sem scheduler automático até GitHub Actions na Fase 5
- Views reprocessam a Bronze a cada query do Power BI (aceitável para o volume atual)

**Decisões adiadas:**
- Materialização como tabelas: revisitar na Fase 4 se houver problema de performance
- dbt Cloud: revisitar na Fase 5 junto com a decisão de orquestração (ADR-0006)
- dbt Contracts nos marts críticos: implementar durante a Fase 3, não pré-requisito para início

---

## Referências

- [dbt Best Practices — How we structure our dbt projects](https://docs.getdbt.com/best-practices/how-we-structure/1-guide-overview)
- [dbt — Naming conventions](https://docs.getdbt.com/blog/on-the-importance-of-naming)
- [BigQuery free tier](https://cloud.google.com/bigquery/pricing#free-tier)
- ADR-0001 — Validação de dados em camadas (Pydantic + Pandera + dbt)
- ADR-0003 — Storage de planilhas e pipeline de ingestão

## Atualização — 2026-06-25

**Status da seção "marts_financeiro":** ⚠️ Suspensa (não implementada na Fase 3)

**Motivo:** As colunas `vl_conta` e `vl_honorario`, base de todos os 5 estudos financeiros descritos na seção "Escopo dos Marts", não passaram por validação de integridade até o momento desta atualização. Não há garantia de que os valores refletem corretamente o faturamento real — gerar análises (dispersão, viés de correção, sazonalidade) sobre dado não validado produziria conclusões com aparência de confiabilidade que não correspondem à realidade, risco maior do que simplesmente não ter o estudo.

**O que muda:**
- A pasta `models/marts/financeiro/` permanece na estrutura do projeto como placeholder, sem nenhum model `.sql` implementado
- O dataset `marts_financeiro` no BigQuery não é criado nesta fase
- Os 5 estudos financeiros ficam formalmente bloqueados até a validação de `vl_conta`/`vl_honorario` ser resolvida

**O que permanece válido:**
- Toda a decisão de arquitetura (dbt Core local, Views, datasets separados por camada, convenções de nomenclatura) continua de pé
- `marts_assistencial` e `marts_modelo` seguem o escopo original sem alteração

**Novo item na lista de deferidos de fim de projeto:** validação de `vl_conta`/`vl_honorario` (ferramenta de validação a definir — possivelmente reconciliação cruzada com o sistema de faturamento/AIH).

## Atualização — 2026-08-21

**Status da seção "marts_financeiro":** Reabertura parcial — 4 de 5 estudos desbloqueados

**Investigação:** Revisão dos 5 estudos originais contra a real dependência de
`vl_conta`/`vl_honorario` revelou que só os Estudos 1 e 2 dependiam de valor
financeiro sem alternativa. Estudo 3 (dias médio) usa `nr_dias`, já presente
na Bronze principal. Estudo 4 (correlação UTI×complexidade) foi resolvido em
2026-08-21 via fonte de dado independente (relatório de movimentações,
ver amendment ADR-0003 e mart_uti). Estudo 5 (sazonalidade) é de volume,
não de valor — coberto por mart_volume_assistencial.

**Nova fonte para Estudos 1 e 2:** relatório "HSR - Análise de Contas"
(Qlik), filtrado por data de "Final Conta" (garante `TEM_DT_FINAL = 'COM FINAL'`,
só contas com processamento encerrado, endereçando a causa raiz da divergência
original com o setor financeiro). Colunas relevantes:
NR_ATENDIMENTO (chave), VALOR, VALOR RECEBIDO, VALOR GLOSA.
vl_honorario permanece fora de escopo.

## Atualização — 2026-08-26

**Status da seção "marts_financeiro":** ✅ Estudos 1 e 2 destravados — fonte validada

**Fonte identificada:** Relatório Qlik "HSR - Análise de Contas", exportado com
filtro "Final Conta" abrangendo todo o histórico de meses disponível (não fatia
mensal única — ver nota de extração abaixo).

**Grão real da fonte:** uma linha por combinação `NR_INTERNO_CONTA` +
`MES_ANO_PRODUCAO`. Um `NR_ATENDIMENTO` pode ter múltiplas `NR_INTERNO_CONTA`
— confirmado como comportamento normal do domínio: fechamento de convênio
ocorre por ciclo de produção, não por atendimento inteiro.

**Regra de agregação validada:** `SUM(VALOR)` agrupado por `NR_INTERNO_CONTA`
(soma parcelas de produção da mesma conta), depois `SUM` novamente por
`NR_ATENDIMENTO` (soma todas as contas do atendimento). Valor incluído
independente de status (parcial ou fechada) — decisão consciente de escopo
exploratório, não fechamento contábil.

**Validação:** 2 atendimentos testados contra o sistema MV (fonte de verdade
operacional). Caso simples (2 linhas/1 conta): match exato. Caso complexo
(7 linhas/6 contas): 5 de 6 contas exatas, 1 conta com diferença de R$ 342,39
(0,38% do total) — tolerância aceita e documentada, não investigada
adicionalmente (dado de sistema legado, fora do escopo deste projeto auditar).

**Nota de extração:** filtro "Final Conta" por mês único captura apenas contas
cujo evento caiu naquele mês — testado e confirmado incompleto (atendimento
1657204 mostrou 3 de 6 contas reais num export de julho isolado). Extração
correta exige selecionar o intervalo de meses completo disponível no filtro,
não uma safra mensal isolada. **Implicação de arquitetura (pendente de decisão):**
o padrão de ingestão `DELETE por safra_mes + APPEND`, usado hoje na Bronze
principal, não se aplica a esta fonte — histórico completo é reextraído a cada
carga, não incremental por mês.

**O que muda:** Estudos 1, 2, 3, 5 saem de suspenso — dado-fonte disponível e
validado (Estudo 3 e 5 já não dependiam de vl_conta, ver amendment 2026-08-21).
`vl_conta`/`vl_honorario` são substituídos por `VALOR` desta fonte, com
granularidade e chave de junção próprias (`NR_ATENDIMENTO`/`NR_INTERNO_CONTA`),
não vêm mais da Bronze de saídas.