# Runbooks Operacionais

Procedimentos passo-a-passo para operações recorrentes do Sistema Preditivo de Classificação SUS.

## Convenções

- Cada runbook é um arquivo Markdown independente
- Inclui: pré-requisitos, passo-a-passo executável, troubleshooting, rollback
- Público-alvo: o próprio Ediney (operações técnicas) e a assistente (operações de interface)
- Nome do arquivo: `RB-NNN-titulo-em-kebab-case.md`

## Runbooks Planejados

| Runbook | Título | Público | Fase |
|---|---|---|---|
| RB-001 | Iniciar o sistema (terminal / .bat) | Ediney | Fase 0 |
| RB-002 | Gerar previsões mensais (uso da GUI) | Assistente | Fase 1 |
| RB-003 | Upload de planilha revisada | Assistente | Fase 2 |
| RB-004 | Retreinar modelo manualmente | Ediney | Fase 5 |
| RB-005 | Investigar alerta de drift | Ediney | Fase 4 |
| RB-006 | Promover challenger a champion | Ediney | Fase 5 |