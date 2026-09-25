# Matriz de Indicadores — Financeiro

**Documento vivo** — atualizado conforme novos indicadores são definidos ou o dado-fonte muda. Não é ADR (decisão imutável); é referência de mapeamento indicador → coluna → status.

Organizado por **indicador**, não por mart, a fonte pode vir de qualquer dataset (`marts_financeiro`, `marts_assistencial`, `marts_modelo`).

---

## Indicadores mapeados

| Indicador | Dimensões de corte disponíveis | Coluna(s) fonte | Status |
|---|---|---|---|
| Dispersão do valor da conta × complexidade/grupo (Estudo 1, ADR-0004) | complexidade_sus, grupo_sus | `valor_faturado`, `complexidade_sus`, `grupo_sus` (`mart_financeiro`) | Disponível |
| Distribuição de valor por classe predita vs. corrigida (Estudo 2, ADR-0004) | grupo_sus/complexidade_sus (real) × previsao_grupo/previsao_complexidade | `valor_faturado`, `grupo_sus`, `previsao_grupo`, `complexidade_sus`, `previsao_complexidade` (`mart_financeiro`) | Disponível, 787 de 3022 registros com predição preenchida (cobertura parcial por safra, mesma lacuna de abril-junho já registrada em `mart_desempenho_modelo`) |
| Dias médio por grupo/complexidade (Estudo 3, ADR-0004) | grupo_sus, complexidade_sus | `nr_dias` (`mart_volume_assistencial`) | Disponível (fora do domínio financeiro) |
| Correlação UTI × complexidade (Estudo 4, ADR-0004) | complexidade_sus | `teve_uti`, `dias_totais_uti` (`mart_uti`) + `complexidade_sus` (`mart_volume_assistencial`) | Disponível (fora do domínio financeiro) |
| Sazonalidade de volume (Estudo 5, ADR-0004) | safra_mes | `mart_volume_assistencial` | Disponível (fora do domínio financeiro; escopo reduzido de "volume e valor" para só "volume" — amendment ADR-0004, 2026-08-21) |
| Faturado × recebido × glosado, por convênio | convenio, fonte_convenio | `valor_faturado`, `valor_recebido`, `valor_glosa`, `convenio`, `fonte_convenio` (`mart_financeiro`) | Disponível, indicador implícito nas colunas do mart, não estava nos 5 estudos originais da ADR-0004; reabre a discussão de "glosa evitada" descartada por falta de tabela de valor de convênio (agora com dado real, não estimado) |