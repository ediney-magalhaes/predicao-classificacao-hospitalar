# Matriz de Indicadores — `marts_assistencial`

**Documento vivo** — atualizado conforme novos indicadores são definidos ou o dado-fonte muda. Não é ADR (decisão imutável); é referência de mapeamento indicador → coluna → status.

**Pré-requisito da Fase 3**, nenhum model de `marts/` deve ser escrito sem que o indicador esteja mapeado aqui primeiro, evita agregação prematura ou grão decidido sem considerar todos os cortes possíveis.

---

## Decisão de grão — `mart_volume_assistencial`

**Grão: igual à Bronze (1 linha = 1 atendimento).** Sem `GROUP BY` no model. Motivo: com ~110 mil registros totais e materialização em View (custo zero), agregar prematuramente por 1-2 dimensões fixas (ex: só por grupo/complexidade) impediria reagregação por qualquer outra dimensão que o Power BI vier a pedir depois, decisão tomada após identificar esse risco no desenho inicial do `int_volumetria_safra` (descartado por não agregar valor sobre a própria staging).

---

## Indicadores mapeados

| Indicador | Dimensões de corte disponíveis | Coluna(s) fonte (Bronze) | Status |
|---|---|---|---|
| Volume de saídas | safra_mes, grupo_sus, complexidade_sus, especialidade, convenio, uf, municipio, tipo_internacao, unidade_saida | qualquer coluna categórica + `safra_mes` | Disponível |
| Distribuição por CID | safra_mes, capitulo_breve, grupo_cid | `cid_1_principal`, `capitulo_breve`, `grupo_cid` | Disponível |
| Sazonalidade | safra_mes | `safra_mes` | Disponível |
| Dias médios de internação | grupo_sus, complexidade_sus | `nr_dias` | Disponível |
| Distribuição por sexo | safra_mes | `sexo` | Disponível |
| Distribuição por faixa etária | safra_mes | `idade` (INT64), enriquecido via seed `faixa_etaria.csv` (LEFT JOIN em `mart_volume_assistencial`) | Disponível |
| Top municípios de origem | safra_mes | `municipio` | Disponível |
| Distribuição por convênio | safra_mes | `convenio` | Disponível (fora do escopo original da ADR-0004, dado existe) |
| Taxa de internação em UTI | atendimento (teve_uti, dias_totais_uti) | **Resolvido via fonte alternativa** (2026-08-21), não usa as 9 colunas originais da Bronze (permanecem com inconsistência não explicada, não confiáveis). Fonte real: relatório de movimentações internas, processado via `mart_uti`. **Não vive em `marts_assistencial`**, está em `marts_modelo`, pois seu consumo real é o Estudo 4 (correlação UTI×complexidade, ADR-0005), não uma métrica assistencial de rotina. Se este indicador for necessário aqui, requer JOIN cross-dataset com `marts_modelo.mart_uti` |

---

## Colunas adicionais identificadas (não mapeadas a indicador ainda)

- `atendimento` (INT64) — candidato a chave única de linha, relevante se algum model futuro precisar de grão por evento individual em vez de agregado
- `prontuario` (INT64) — identificador de paciente; relevante para análises de reinternação, fora do escopo atual