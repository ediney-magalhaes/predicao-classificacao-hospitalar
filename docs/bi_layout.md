# Layout dos Relatórios — Looker Studio

**Documento vivo** — atualizado conforme componentes são construídos ou o
escopo muda em relação ao planejado. Não é ADR; é referência do que cada
página do BI realmente entrega, mantida em paralelo às matrizes de
indicadores (`docs/matriz_indicadores*.md`).

---

## Relatório 1 — Executivo

### Página 1 — Visão Geral (concluída, 2026-09-25)

| Componente | Fonte | Status |
|---|---|---|
| Total de Saídas | `mart_volume_assistencial`, Contagem de registros | Conforme planejado |
| % Classificação das saídas por grupo | `grupo_sus`, Barras horizontais + % do total | Conforme planejado |
| % Classificação das saídas por complexidade | `complexidade_sus`, Barras horizontais + % do total | Conforme planejado |
| Distribuição do número de saídas (sazonalidade) | `safra_data`, Série temporal | Conforme planejado |
| **% saídas, segundo capítulo breve CID-10** | `capitulo_breve`, Donut | **Escopo alterado** — ver nota abaixo |
| **Distribuição Geográfica das saídas** | `municipio` + `uf`, Google Maps (bolhas) | **Formato alterado** — ver nota abaixo |

**Nota — mudança de escopo, item CID (2026-09-25):** o layout original
previa "Top 10 CIDs" (`cid_1_principal`, ranking de códigos individuais).
Testado e descartado: CID-10 no nível de código tem cauda longa extrema
(milhares de valores possíveis), resultando em "Outros" dominando ~90%+
do gráfico e códigos isolados sem significado pra audiência executiva sem
contexto clínico. Substituído por distribuição por **capítulo** do CID-10
(`capitulo_breve`, ~20 categorias possíveis), onde as 9 categorias
nomeadas somam ~90% e "Outros" fica residual. `cid_1_principal` continua
disponível no mart pra uso técnico futuro (Relatório 2 ou drill-down).

**Nota — mudança de formato, item Municípios (2026-09-25):** o layout
original previa "Top municípios" como ranking (Barras horizontais). Trocado
por mapa (Google Maps, bolhas) — decisão consciente de priorizar "alcance
geográfico" (pergunta que a audiência executiva valoriza) sobre "ranking
exato por posição", que o formato de mapa comunica pior que barra. Exigiu
campo calculado `municipio_geocodificacao` (concatenação `municipio, uf,
Brasil`) pra evitar ambiguidade de geocodificação (casos confirmados:
"Cáceres"/MT resolvendo pra Espanha, "Sinop"/MT resolvendo pra Turquia).

**Nota — dado ausente na sazonalidade (2026-09-25):** existe um gap real
de 15 safras (todo 2025 + jan-mar/2026) em `mart_volume_assistencial`,
conhecido e confirmado. Decisão consciente: o gráfico de série temporal
mostra esse período como **zero literal** (comportamento padrão do Looker
Studio pra datas ausentes em dimensão de Data contínua), não como
interpolação nem quebra de linha. Decisão de Ediney, mantida como está.

### Página 2 — Perfil do Paciente (não iniciada)
### Página 3 — Financeiro & Recursos (não iniciada)

## Relatório 2 — Monitoramento Técnico (não iniciado)