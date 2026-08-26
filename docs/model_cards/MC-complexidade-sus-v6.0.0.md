# Model Card: COMPLEXIDADE_SUS — v6.0.0

**Data de treino:** Março/2026
**Última atualização deste documento:** 2026-08-21
**Status:** Em produção (champion único, sem versionamento formal de challenger ainda, Fase 5)

## Visão Geral

Classifica internações hospitalares em um de 4 níveis de complexidade SUS:
Atenção Básica, Média Complexidade, Alta Complexidade, Não se Aplica.

## Dados de Treino

- **Fonte:** Bronze do BigQuery (`bronze_saidas_anonimizado`)
- **Filtro temporal:** Dados a partir de 2020 (combate a data drift histórico)
- **Algoritmo:** LightGBM
- **Balanceamento:** SMOTE via `ImbPipeline`, aplicado apenas nos dados de
  treino durante validação cruzada
- **Features (10, na ordem do treino):** idade, nr_dias, cid_entrada,
  procedimento_entrada, cid_1_principal, cirurgia, CAPÍTULO BREVE, GRUPO,
  sexo, medico_resp_atend
- **Tamanho do conjunto de avaliação:** 12.829 registros

## Métricas por Classe

| Classe | Precision | Recall | F1-score | Support |
|---|---|---|---|---|
| Média Complexidade | 0.97 | 0.98 | 0.97 | 10.872 |
| Alta Complexidade | 0.88 | 0.81 | 0.85 | 1.896 |
| Atenção Básica | 0.82 | 0.76 | 0.79 | 37 |
| Não se Aplica | 0.86 | 0.60 | 0.71 | 20 |
| Classe não identificada (`-`) | 0.00 | 0.00 | 0.00 | 4 |

**Acurácia geral:** 0.95
**Macro avg (não ponderado por classe):** Precision 0.71, Recall 0.63, F1 0.66
**Weighted avg (ponderado por classe):** Precision 0.95, Recall 0.95, F1 0.95

## Limitações Conhecidas

- **Gap entre macro e weighted average (0.66 vs 0.95):** desempenho
  concentrado na classe majoritária (Média Complexidade, 85% dos casos).
  As três classes minoritárias somadas representam menos de 15% do
  conjunto de avaliação, e seu desempenho é substancialmente pior que a
  acurácia geral sugere.
- **Recall baixo em "Não se Aplica" (0.60, apenas 20 casos):** o modelo
  deixa passar 40% dos casos reais dessa classe — o menor recall entre
  todas as classes reais do domínio, com volume pequeno o suficiente
  para alta variância na métrica.
- **Classe `-` (4 registros, F1 zero):** mesma origem provável que no
  modelo GRUPO_SUS — investigar antes do próximo retreino.
- **Sem calibração de probabilidade:** mesmo ponto do modelo GRUPO_SUS
  (ver ADR-0009, Fase 6).
- **Sem retreino desde março/2026.**

## Casos de Uso Pretendidos

- Suporte à decisão para triagem inicial de complexidade SUS, com revisão
  humana obrigatória (ciclo HITL)
- Priorização de revisão manual para casos de baixa confiança (<0.7)

## Casos de Uso Proibidos

- Decisão automática sem revisão humana
- Uso para "Atenção Básica" ou "Não se Aplica" sem atenção redobrada na
  revisão, volume de treino pequeno (37 e 20 casos, respectivamente)
  torna o desempenho nessas classes menos confiável que a média geral sugere