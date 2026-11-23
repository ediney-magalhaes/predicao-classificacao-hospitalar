# Runbooks Operacionais

Procedimentos passo-a-passo para operações recorrentes do Sistema Preditivo de Classificação SUS.

## Convenções

- Cada runbook é um arquivo Markdown independente
- Inclui: pré-requisitos, passo-a-passo executável, troubleshooting, rollback
- Público-alvo: o próprio Ediney (operações técnicas) e a assistente (operações de interface)
- Nome do arquivo: `RB-NNN-titulo-em-kebab-case.md`

## Runbooks

| Runbook | Título | Público | Fase | Status |
|---|---|---|---|---|
| RB-001 | Iniciar o sistema (terminal / .bat) | Ediney | Fase 0 | Escrito |
| RB-002 | Gerar previsões mensais (uso da GUI) | Assistente | Fase 1 | Escrito |
| RB-003 | Upload de correções e movimentações mensais | Assistente | Fase 2 | Escrito |
| RB-004 | Enviar o financeiro mensal (Qlik → Bronze) | Ediney | Fase 3 | Escrito |
| RB-005 | Retreinar modelo manualmente | Ediney | Fase 5 | Planejado |
| RB-006 | Investigar alerta de drift | Ediney | Fase 4 | Planejado |
| RB-007 | Promover challenger a champion | Ediney | Fase 5 | Planejado |