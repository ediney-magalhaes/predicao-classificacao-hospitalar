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


### Página 2 — Perfil do Paciente (concluída, 2026-10-01)

| Componente | Fonte | Status |
|---|---|---|
| Distribuição das saídas por faixa etária (pirâmide) | `faixa_etaria` + `ordem_faixa_etaria`, Barras horizontais agrupadas (F/M) | Conforme planejado |
| Distribuição das saídas, segundo fonte pagadora | `fonte_convenio`, Donut | **Escopo alterado** — ver nota abaixo |
| Relação do tipo de internação na entrada e a classificação na saída | `tipo_internacao` × `grupo_sus`, Tabela dinâmica com mapa de calor | **Adicionado fora do escopo original** — ver nota abaixo |
| Distribuição do tempo médio de hospitalização, segundo capítulo breve | `capitulo_breve` + `nr_dias` (média) + Contagem, Barras agrupadas (dois eixos) | **Adicionado fora do escopo original** — ver nota abaixo |
| Distribuição do número de saídas, segundo complexidade x capítulo breve | `complexidade_sus` × `capitulo_breve`, Barras 100% empilhadas | **Adicionado fora do escopo original** — ver nota abaixo |
| Distribuição das saídas, segundo especialidade | `especialidade`, Treemap | Conforme planejado |

**Nota — mudança de escopo, item fonte pagadora (2026-10-01):** o escopo
original previa "convênio" como componente. Construímos `fonte_convenio`,
categoria agrupada por tipo de operadora (via `mapa_convenio_fonte`, por
`registro_ans`), não o nome bruto do convênio, mesma lógica da Página 1
com CID (nível de código é inviável, nível de categoria funciona). Durante
a sessão, descobrimos que 2.256 de 52.800 registros ficavam sem
`fonte_convenio` porque o join por `registro_ans` não encontrava
correspondência, a maioria era `PARTICULAR`/`HSR - PARTICULAR` (2.086
registros), que não tem registro na ANS por não ser operadora de saúde.
Decisão: criar a categoria "Particular" no mart para esses casos, e mandar
o restante dos nulos (170 registros, ex. convênios fechados de empresas)
para "Outros", a mesma categoria "Outros" que já vinha do mapeamento ANS
(348 registros), por decisão consciente de não abrir uma terceira
categoria para algo residual.

**Nota — mudança de escopo, item tipo de internação (2026-10-01):** o
escopo original previa "tipo de internação" como componente isolado
(distribuição simples). Evoluiu para um cruzamento com `grupo_sus` durante
a sessão: a distribuição sozinha não respondia a pergunta real de interesse,
que é a convergência entre o tipo de internação registrado na entrada
e a classificação de faturamento gerada na saída.
Implementado como tabela dinâmica com mapa de calor (barras e
donut descartados por ilegibilidade com 13 categorias de tipo de
internação × 8 de grupo SUS). Achado relevante que motiva o componente:
Internação Clínica Urgência tem 9.134 casos (66%) como Procedimentos
clínicos, mas 4.014 (29%) saem como Procedimentos cirúrgicos, divergência
que merece investigação futura, não resolvida nesta sessão.

**Nota — componente fora do escopo original, tempo de hospitalização × capítulo CID (2026-10-01):**
Adicionado na sessão a partir de `nr_dias`, campo do mart sem componente próprio até então.
Cruza tempo médio de internação (`nr_dias`, média) com `capitulo_breve`,
reaproveitando o nível de agregação já validado na Página 1 para CID-10.

**Nota — componente fora do escopo original, complexidade × capítulo CID (2026-10-01):**
`complexidade_sus` já tinha um componente de distribuição isolada na Página 1 (Visão Geral);
nesta página ela aparece cruzada com `capitulo_breve`, para responder uma pergunta diferente,
em quais capítulos CID a alta complexidade se concentra, e não apenas a proporção geral de complexidade.
Implementado como barras 100% empilhadas.

### Página 3 — Financeiro & Recursos (não iniciada)

## Relatório 2 — Monitoramento Técnico (não iniciado)