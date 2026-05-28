# ADR-0003: Storage de Planilhas (Input e Revisadas)

## Status

**Aceita** — 22/05/2026

## Y-Statement

No contexto do ciclo HITL onde a assistente gera predições e devolve correções, enfrentando a necessidade de armazenar planilhas com dados sensíveis de pacientes de forma segura e acessível, decidimos usar a pasta de rede interna (drive W:) como storage primário com pipeline de ingestão anonimizada para o BigQuery, para manter dados sensíveis dentro da rede do hospital e reaproveitar o fluxo de trabalho que o setor já pratica, aceitando a dependência da infraestrutura de rede interna do hospital e a limitação de acesso apenas dentro da rede.

## Contexto

O sistema preditivo de classificação SUS opera com um ciclo Human-in-the-Loop (HITL):

1. Assistente faz upload de 3 planilhas brutas → modelo gera predições
2. Assistente corrige predições no Excel → salva planilha revisada
3. Planilha revisada alimenta a Bronze no BigQuery (dados anonimizados) para retreino

As planilhas contêm dados sensíveis de pacientes (nome, CPF, prontuário) e devem permanecer sob controle do setor, em conformidade com a LGPD. O setor já possui uma pasta de rede compartilhada (drive W:) com 422 GB livres, de uso permanente, onde historicamente armazena as planilhas revisadas de todos os meses.

### Decision Drivers

- Dados sensíveis de pacientes não podem sair da rede interna do hospital
- A assistente já utiliza a pasta W: como storage no fluxo atual
- O histórico de planilhas revisadas na W: foi a fonte que alimentou o treino inicial do modelo
- Planilhas revisadas também são usadas para reports a outra instituição (uso duplo)
- Custo deve ser R$ 0,00
- Zero dependência da TI para operar

## Opções Consideradas

### Opção 1 — Pasta de rede interna (drive W:)

Usar o drive W: que já existe como storage primário. Organizar por safra mensal. Pipeline de ingestão lê da W:, anonimiza e faz append na Bronze do BigQuery.

✅ Já é o storage de fato — zero mudança no fluxo da assistente

✅ Dados sensíveis nunca saem da rede interna

✅ Serve duplo propósito (ML + reports externos)

✅ Custo zero, sem dependência de TI

✅ 422 GB livres — suficiente para décadas de planilhas (~1 MB/mês)


❌ Sem versionamento nativo (precisa de convenção de nomes)

❌ Sem backup automatizado (depende da política de backup da TI na rede)

❌ Acessível apenas dentro da rede do hospital

### Opção 2 — GCS Bucket (Google Cloud Storage)

Criar um bucket no mesmo projeto GCP do BigQuery. Upload via API no pipeline.

✅ Versionamento nativo de objetos

✅ Backup e durabilidade garantidos (99.999999999%)

✅ Acessível de qualquer lugar com credenciais

✅ Integração nativa com BigQuery

❌ Dados sensíveis saem da rede interna → requer análise de conformidade LGPD

❌ Custo potencial (free tier do GCS é 5 GB, planilhas são pequenas mas acumulam)

❌ Mudança no fluxo da assistente — precisa aprender a usar upload na GUI em vez de salvar na W:

❌ Dependência de internet para funcionar

### Opção 3 — Híbrido (W: + GCS)

W: como storage primário dos dados brutos. GCS recebe apenas cópia anonimizada.

✅ Melhor dos dois mundos em teoria

❌ Complexidade operacional: dois storages para gerenciar

❌ GCS recebendo dados anonimizados duplica o que já vai para o BigQuery

❌ Overhead sem benefício claro sobre a Opção 1

## Decisão

**Opção escolhida: Pasta de rede interna (drive W:)**, porque:

1. Já é o storage que o setor usa — mudança zero no fluxo da assistente
2. Dados sensíveis permanecem na rede interna do hospital
3. O histórico existente na W: é a fonte de verdade que treinou o modelo original
4. Custo zero, sem dependência da TI
5. O duplo uso (ML + reports) é atendido naturalmente

### Organização na W:

```
W:\...\Epidemio\
├── 2026\
│   ├── Banco Epidemio - Janeiro 2026.xlsx              # Planilha revisada pela assistente
│   ├── Banco Epidemio - Janeiro 2026 - PREDICAO.xlsx   # Output do modelo (cópia de referência)
│   ├── Banco Epidemio - Fevereiro 2026.xlsx
│   ├── Banco Epidemio - Fevereiro 2026 - PREDICAO.xlsx
│   └── ...
├── 2025\
│   └── ...
└── historico desde 2012
```

### Pipeline de ingestão

```
W: (planilha revisada, upload pela assistente na aba 2 da GUI)
  → Validação de schema (Pandera) com normalização case-insensitive
  → Localização da predição original na W: (sufixo - PREDICAO)
  → Detecção de diferenças pareadas (original vs revisão)
  → Enriquecimento CID (merge com dicionário → capitulo_breve, grupo_cid)
  → Anonimização (SHA-256 + salt nos campos PII)
  → DELETE por safra_mes na Bronze (garante idempotência)
  → Append na Bronze (BigQuery)
  → Registro de auditoria (BigQuery: audit.hitl_events)
```

## Consequências

### Positivas

- Zero atrito para a assistente — ela continua salvando onde sempre salvou
- Dados sensíveis nunca saem do perímetro da rede hospitalar
- Pipeline de ingestão consome da W: e entrega dados limpos no BigQuery
- Custo mensal: R$ 0,00

### Negativas

- Sem versionamento nativo — mitigado pela convenção de nomes por safra
- Sem backup automatizado no nível do setor — mitigado pelo fato de que os dados anonimizados existem no BigQuery como backup funcional
- Acesso limitado à rede do hospital — aceitável dado o requisito de segurança

### Riscos

- Se a TI fizer limpeza de arquivos antigos na W:, planilhas podem ser perdidas. **Mitigação:** dados anonimizados estão no BigQuery; planilhas com mais de 2 anos podem ser arquivadas em subpasta separada
- Se a W: ficar indisponível, o ciclo HITL para. **Mitigação:** baixa probabilidade (infraestrutura estável); em emergência, planilha pode ser processada localmente

## Referências

- ADR-0001: Validação de dados em camadas (Pandera valida na ingestão)
- ADR-0002: Hosting da GUI Streamlit (local na rede do hospital)
- Fase 2 do Roadmap: Ciclo HITL Automatizado