# Architecture Decision Records (ADRs)

Registro estruturado das decisões arquiteturais do Sistema Preditivo de Classificação SUS.

## Convenções

- **Formato padrão:** MADR 4.0 com Y-Statement no topo (ver [ADR-0000](0000-adotar-madr-como-formato-de-adr.md))
- **Formato leve:** Nygard simplificado para decisões menores e facilmente reversíveis
- **Numeração:** sequencial, 4 dígitos, zero-padded (0000, 0001, ...)
- **Nome do arquivo:** `NNNN-titulo-em-kebab-case.md`
- **Idioma:** Português do Brasil
- **Regra de triagem:** se a decisão precisa de comparação estruturada entre alternativas → MADR completo. Se cabe em 2 minutos → Nygard leve.

## Índice

| ADR | Título | Status | Data |
|---|---|---|---|
| [0000](0000-adotar-madr-como-formato-de-adr.md) | Adotar MADR como formato padrão de ADR | Aceita | 2026-04-27 |
| [0001](0001-validacao-de-dados-em-tres-camadas.md) | Validação de dados em três camadas (Pydantic + Pandera + dbt) | Aceita | 2026-04-27 |

## ADRs Planejadas

| ADR | Tema | Fase | Status |
|---|---|---|---|
| 0002 | Hosting da GUI Streamlit | Fase 1 | Pendente |
| 0003 | Storage de planilhas (input + revisada) | Fase 2 | Pendente |
| 0004 | Model Registry | Fase 5 | Pendente |
| 0005 | Monitoramento de drift | Fase 4 | Pendente |
| 0006 | Orquestração de pipelines | Fase 5 | Pendente |
| 0007 | Documentação técnica | Fase 8 | Pendente |
| 0008 | Estratégia de testes | Fase 8 | Pendente |
| 0009 | Calibração de probabilidades | Fase 6 | Pendente |
| 0010 | Conformal Prediction | Fase 6 | Pendente |

## Templates

- [`adr-template-completo.md`](adr-template-completo.md) — MADR 4.0 com Y-Statement (decisões de peso)
- [`adr-template-leve.md`](adr-template-leve.md) — Nygard simplificado (decisões menores)