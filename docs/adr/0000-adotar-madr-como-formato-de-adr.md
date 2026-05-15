# ADR-0000: Adotar MADR como formato padrão de Architecture Decision Records

> No contexto da governança técnica do Sistema Preditivo de Classificação SUS, enfrentando a necessidade de registrar decisões arquiteturais de forma estruturada e rastreável, decidimos por MADR 4.0 com Y-Statement como formato padrão (e Nygard simplificado como formato leve) e descartamos usar apenas Nygard puro, Y-Statement isolado ou documentação ad-hoc, para alcançar rastreabilidade, rigor comparativo e valor de portfólio, aceitando um overhead marginalmente maior (~5 min) por ADR em relação ao Nygard puro.

## Status

**Aceita**

**Data:** 2026-04-27
**Decisor(es):** Ediney Magalhães

## Contexto e Problema

O projeto está em fase de construção ativa com dezenas de decisões arquiteturais pela frente (hosting, model registry, drift monitoring, orquestração, testes). Sem registro estruturado, o raciocínio por trás das escolhas se perde em conversas e na memória do líder técnico — gerando retrabalho, decisões revisitadas sem contexto, e dificuldade de comunicar o projeto em entrevistas ou apresentações.

## Drivers da Decisão

* **Bus factor:** projeto operado por 1 pessoa técnica — registro é seguro contra perda de contexto
* **Portfólio:** ADRs bem escritas são diferencial em entrevistas para vagas Senior/Staff
* **Pragmatismo:** nem toda decisão merece o mesmo nível de rigor — precisamos de dois "pesos"
* **Custo:** R$ 0 — é só Markdown no repositório Git

## Opções Consideradas

1. MADR 4.0 com Y-Statement (completo) + Nygard (leve)
2. Nygard puro para tudo
3. Y-Statement isolado
4. Documentação ad-hoc (sem template)

## Resultado da Decisão

**Opção escolhida:** "MADR 4.0 com Y-Statement + Nygard leve", porque combina rigor comparativo para decisões de peso com agilidade para decisões menores, alinhando-se ao Formato de Discussão Estruturada já adotado no projeto.

### Regra de Triagem

| Critério | MADR completo | Nygard leve |
|---|---|---|
| Quando usar | Escolha entre alternativas reais, difícil de reverter, valor de portfólio | Poucas alternativas, facilmente reversível, consequência de ADR maior |
| Exemplos | Ferramenta de drift, Model Registry, hosting da GUI | Formato de hash, versão mínima do Python, convenção de nomes |
| Seções obrigatórias | Y-Statement, Context, Drivers, Options com Pros/Cons, Decision, Consequences | Title, Status, Context, Decision, Consequences |

**Heurística:** "Se eu precisaria do Formato de Discussão Estruturada (seção 5 do system prompt) para decidir, é MADR completo. Se cabe em 2 minutos de conversa, é Nygard leve."

### Confirmação

* Todo PR que implementa uma decisão arquitetural deve referenciar a ADR correspondente
* Code review inclui verificação: "essa mudança tem ADR? Precisa?"

### Consequências

* **Positiva:** Rastreabilidade completa do "porquê" de cada escolha técnica
* **Positiva:** Material pronto para entrevistas, posts e apresentações executivas
* **Positiva:** Dois templates evitam over-engineering em decisões triviais
* **Negativa:** Overhead de ~10-15 min por ADR completa (aceitável dado o volume de ~1-2 por fase)

## Mais Informações

* Template MADR oficial: https://github.com/adr/madr (v4.0.0, setembro 2024)
* Referência original Nygard: https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions
* Diretório deste projeto: `docs/adr/`
* Templates disponíveis: `adr-template-completo.md` (MADR) e `adr-template-leve.md` (Nygard)