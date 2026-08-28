# ADR-0005 — Testes Estatísticos Formais como Produto Recorrente

**Status:** Aceita

**Data:** 2026-07-27

**Autor:** Ediney Magalhães

**Contexto da fase:** Fase 3 — Camada Analítica + BI

---

## Y-Statement

**Para** a diretoria e para quem cuida do modelo,
**que precisam de** respostas estatisticamente rigorosas sobre associação, tendência e significância — não só visualização descritiva,
**o** projeto adota um script Python (`scripts/analise_estatistica_mensal.py`), rodando `scipy.stats` sobre a Bronze/marts já validados, disparado manualmente junto ao ciclo de ingestão HITL mensal, gerando um relatório Markdown versionado por safra,
**para conseguir** que qui-quadrado, Kruskal-Wallis, Spearman, Wilson, McNemar, Cochran-Armitage e poder amostral estejam disponíveis sem que ninguém precise solicitar,
**aceitando que** a execução continua manual até a Fase 5 (GitHub Actions, ADR-0006), igual ao restante do pipeline dbt hoje.

## Contexto

A camada dbt cobre estatística descritiva. Teste de hipótese formal não tem função nativa completa em SQL do BigQuery e produz interpretação textual, não só número — não cabe em mart nem em dashboard sem perder contexto.

## Decisão

Script Python dedicado, execução manual acoplada ao ciclo mensal de ingestão HITL, saída em Markdown versionado em `docs/relatorios_estatisticos/YYYY-MM.md`.

## Consequências

**Positivas:** custo zero, reaproveita `scipy.stats` já maduro, resultado versionado e auditável no Git, mesmo padrão de artefato que Model Cards/Runbooks.

**Negativas:** execução manual até Fase 5 (mesma dívida já aceita pro resto do pipeline); relatório em Markdown não é consumível direto pelo Power BI (decisão consciente, não lacuna).