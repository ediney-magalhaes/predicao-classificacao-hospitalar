# Model Card: GRUPO_SUS — v6.0.0

**Data de treino:** Março/2026
**Última atualização deste documento:** 2026-08-21
**Status:** Em produção (champion único, sem versionamento formal de challenger ainda, Fase 5)

## Visão Geral

Classifica internações hospitalares em uma de 4 categorias de faturamento
SUS: Procedimentos cirúrgicos, Procedimentos clínicos, Procedimentos com
finalidade diagnóstica, Órteses/próteses/materiais especiais (OPME).

## Dados de Treino

- **Fonte:** Bronze do BigQuery (`bronze_saidas_anonimizado`)
- **Filtro temporal:** Dados a partir de 2020 (combate a data drift histórico)
- **Algoritmo:** LightGBM
- **Balanceamento:** SMOTE via `ImbPipeline`, aplicado apenas nos dados de
  treino durante validação cruzada (não vaza para o conjunto de teste)
- **Features (10, na ordem do treino):** idade, nr_dias, cid_entrada,
  procedimento_entrada, CAPÍTULO BREVE, GRUPO, cirurgia, cid_1_principal,
  sexo, medico_resp_atend
- **Tamanho do conjunto de avaliação:** 12.829 registros

## Métricas por Classe

| Classe | Precision | Recall | F1-score | Support |
|---|---|---|---|---|
| Procedimentos cirúrgicos | 0.95 | 0.95 | 0.95 | 6.533 |
| Procedimentos clínicos | 0.94 | 0.96 | 0.95 | 5.733 |
| Procedimentos com finalidade diagnóstica | 0.94 | 0.85 | 0.89 | 544 |
| Órteses, próteses e materiais especiais | 0.83 | 0.67 | 0.74 | 15 |
| Classe não identificada (`-`) | 0.00 | 0.00 | 0.00 | 4 |

**Acurácia geral:** 0.95
**Macro avg (não ponderado por classe):** Precision 0.73, Recall 0.68, F1 0.71
**Weighted avg (ponderado por classe):** Precision 0.95, Recall 0.95, F1 0.95

## Limitações Conhecidas

- **Gap entre macro e weighted average (0.71 vs 0.95):** o modelo tem bom
  desempenho nas classes majoritárias (Cirúrgico, Clínico juntas, 95% dos
  casos), mas degrada nas minoritárias, especialmente OPME (F1 0.74,
  apenas 15 casos no conjunto de avaliação). A acurácia geral de 95% mascara
  esse desempenho desigual, não deve ser citada isoladamente sem o
  detalhamento por classe.
- **Classe `-` (4 registros, F1 zero):** provável erro de rótulo ou valor
  ausente que não foi filtrado na limpeza. Não representa uma categoria
  real do domínio SUS. Requer investigação antes do próximo retreino,
  se persistir, indica falha na pipeline de limpeza upstream.
- **Volume pequeno da classe OPME:** com apenas 15 casos no conjunto de
  avaliação, a métrica de 0.74 tem alta variância, poucas predições
  erradas mudam substancialmente o F1. Não deve ser tratada como medida
  estável até o volume crescer.
- **Sem calibração de probabilidade:** o score de confiança reflete
  confiança relativa do modelo, não probabilidade real (ver ADR-0009,
  Fase 6).
- **Sem retreino desde março/2026:** estas métricas refletem o snapshot
  de treino original; nenhum retreino formal ocorreu até a data deste
  documento (2026-08-21).

## Mitigação em Produção

**Business Rule Override:** corrige predições onde o modelo classifica
"Procedimentos clínicos" mas há registro de cirurgia realizada, trava
de segurança específica para o erro mais custoso da classe majoritária
mal classificada.

## Casos de Uso Pretendidos

- Suporte à decisão para triagem inicial de faturamento SUS, com revisão
  humana obrigatória (ciclo HITL)
- Priorização de revisão manual para casos de baixa confiança (<0.7)

## Casos de Uso Proibidos

- Decisão automática sem revisão humana (o sistema é HITL por desenho,
  não substituto de revisão)
- Uso para classes com baixo volume de treino (OPME, finalidade
  diagnóstica) sem atenção redobrada na revisão, desempenho nessas
  classes é significativamente menos confiável que a acurácia geral sugere