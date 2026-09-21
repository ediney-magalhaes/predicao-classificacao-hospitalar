# Matriz de Indicadores — Modelo

**Documento vivo** — atualizado conforme novos indicadores são definidos ou o dado-fonte muda. Não é ADR (decisão imutável); é referência de mapeamento indicador → coluna → status.

Organizado por **indicador**, não por mart, a fonte pode vir de qualquer dataset (`marts_modelo`, `marts_assistencial`).

---

## Indicadores mapeados

| Indicador | Dimensões de corte disponíveis | Coluna(s) fonte | Status |
|---|---|---|---|
| Taxa de correção humana, por safra | safra_mes | `taxa_correcao_grupo`, `taxa_correcao_complexidade` (`mart_taxa_correcao`) | Disponível |
| Volume de correções por tipo (grupo, complexidade, ambos) | safra_mes | `correcoes_grupo`, `correcoes_complexidade`, `correcoes_ambos` (`mart_taxa_correcao`) | Disponível |
| Tempo médio de revisão | safra_mes | `tempo_revisao_min` (`mart_taxa_correcao`) | Disponível |
| Top 5 transições de erro mais frequentes, por safra | safra_mes, variavel (grupo/complexidade) | `previsto`, `real`, `total`, `posicao` (`mart_transicoes_erro`) | Disponível |
| Acertos/erros do modelo por classe, por safra | safra_mes | `acertos_grupo`, `erros_grupo`, `acertos_complexidade`, `erros_complexidade` (`mart_desempenho_modelo`) | Disponível|
| Precision/Recall/F1 por classe individual, por safra | safra_mes, variavel, classe | `tp`, `fp`, `fn`, `precision`, `recall`, `f1_score` (`mart_precisao_recall_modelo`) | Disponível|
| Versão do modelo em produção, por safra | safra_mes | `versao_modelo` (`mart_taxa_correcao`, `mart_desempenho_modelo`) | Disponível |
| Taxa de UTI por atendimento (teve UTI, tempo total) | atendimento | `teve_uti`, `dias_totais_uti`, `qtd_passagens_uti` (`mart_uti`) | Disponível, grão de atendimento, sem dimensão temporal própria (ver nota abaixo) |
| Passagens de UTI ao longo do tempo, por período de movimentação | safra_mes (da movimentação, não do atendimento) | `data_hora_entrada`, `data_hora_saida`, `eh_uti`, `safra_mes` (`int_movimentacoes_uti`) | Disponível, grão de passagem individual, não de atendimento; usar esta fonte (não `mart_uti`) para qualquer corte temporal |

**Nota sobre `mart_uti` e período:** o mart não carrega `safra_mes` por decisão estrutural, não por lacuna esquecida. Grão é 1 linha por atendimento, agregando todas as passagens de UTI; atendimentos com passagens em mais de uma safra de movimentação (confirmado: pelo menos 21 casos) tornariam qualquer `safra_mes` única nessa linha uma escolha arbitrária, não um fato. Análise temporal de UTI deve consumir `int_movimentacoes_uti` diretamente (grão de passagem, uma safra real por linha).