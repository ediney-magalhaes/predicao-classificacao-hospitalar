# ADR-0001: Adotar validação de dados em três camadas (Pydantic + Pandera + dbt)

> No contexto do pipeline preditivo de classificação SUS, enfrentando o risco de dados inválidos gerarem predições incorretas e contaminarem o warehouse, decidimos por uma estratégia de validação em três camadas — Pydantic v2 para configs/objetos Python, Pandera para DataFrames de entrada, e dbt tests/contracts para o warehouse — e descartamos Great Expectations (centralizado) e validação apenas via dbt (tardia), para alcançar validação precoce no ponto de entrada, separação de responsabilidades e ROI de aprendizado maximizado, aceitando a complexidade de manter três ferramentas em vez de uma.

## Status

**Aceita**

**Data:** 2026-04-27
**Decisor(es):** Ediney Magalhães

## Contexto e Problema

Os dados do sistema entram como planilha XLSX (upload manual pela assistente), transitam por scripts Python (limpeza, feature engineering, inferência) e repousam no BigQuery (Bronze → Silver → Gold via dbt). Cada estágio tem natureza diferente:

* **Entrada (XLSX):** dados tabulares com risco de colunas faltantes, tipos errados, valores fora de domínio. Se não validados aqui, o modelo gera predição com lixo — e a assistente não tem como perceber.
* **Configs e objetos Python:** settings de ambiente (.env), parâmetros de modelo, outputs estruturados (ex: SHAP values). Erros de tipo aqui causam falhas silenciosas ou exceções opacas.
* **Warehouse (BigQuery):** integridade referencial, freshness, regras de negócio em SQL. Validação aqui é a última linha de defesa, mas chega tarde — o dano (predição incorreta) já ocorreu.

**O pecado capital é validar tarde.** Se a validação só acontece no dbt (depois que o dado já entrou no warehouse), a assistente já recebeu uma planilha com predições baseadas em dados inválidos.

## Drivers da Decisão

* **Validação precoce:** erro detectado na entrada custa ordens de magnitude menos que erro detectado na Gold
* **Volume:** ~900 linhas/mês — não justifica ferramentas enterprise-grade
* **Time:** 1 pessoa técnica (Ediney) + 1 assistente não-técnica — simplicidade operacional é crítica
* **Custo:** R$ 0,00 — todas as ferramentas devem ser open source e free
* **ROI de carreira:** cada ferramenta aprendida deve ter alta empregabilidade no mercado brasileiro
* **Separação de responsabilidades:** cada camada valida o que faz sentido na sua jurisdição

## Opções Consideradas

1. Great Expectations como ferramenta única para todas as camadas
2. Pydantic v2 (configs) + Pandera (DataFrames) + dbt tests/contracts (warehouse)
3. Apenas dbt tests/contracts (validação só no warehouse)
4. Validação manual com asserts e try/except em Python puro

## Resultado da Decisão

**Opção escolhida:** "Pydantic v2 + Pandera + dbt tests/contracts", porque cada ferramenta é a melhor no seu domínio, o overhead de manter três ferramentas leves é menor que o de configurar uma ferramenta pesada, e o ROI de aprendizado é maximizado (Pydantic é onipresente em FastAPI/LLMs, Pandera é leve e já conhecido, dbt já é diferencial do Ediney).

### Confirmação

* **Pydantic:** todo `BaseSettings` e todo Pydantic model deve ter teste unitário (pytest) validando rejeição de input inválido
* **Pandera:** schema da planilha XLSX deve ter teste com fixture de dados inválidos (colunas faltantes, tipos errados, valores fora de domínio)
* **dbt:** `dbt test` roda no CI (GitHub Actions) e bloqueia merge se falhar
* **Code review:** PRs que adicionam novo campo de entrada devem atualizar os schemas das três camadas

### Consequências

* **Positiva:** Erro na planilha é detectado antes da inferência — assistente recebe mensagem clara, não predição silenciosamente errada
* **Positiva:** Settings validados pelo Pydantic eliminam classe inteira de bugs de configuração (chave de API faltante, path errado, tipo inválido)
* **Positiva:** dbt contracts garantem que mudanças no schema da Bronze/Silver/Gold não passam despercebidas
* **Positiva:** Ediney aprende Pydantic v2, que é requisito em ~70% das vagas Python sênior que envolvem APIs ou LLMs
* **Negativa:** Três ferramentas para manter, atualizar e ensinar (mitigado pelo fato de que cada uma é leve e tem escopo claro)
* **Negativa:** Pandera tem adoção menor que Great Expectations no mercado — mas o uso aqui é minimalista e o Ediney já tem experiência prévia (projeto Dengue-MT)

## Prós e Contras das Opções

### Great Expectations (centralizado)

Framework completo de validação de dados com suítes de expectativas, data docs e integração com orquestradores.

* ✅ Ferramenta única para todas as camadas — consistência
* ✅ Altíssima adoção no mercado, especialmente em times grandes
* ✅ Data docs geram documentação visual das validações
* ❌ Curva de aprendizado íngreme para configurar bem (YAML, stores, checkpoints)
* ❌ Sofisticação desproporcional ao volume (900 linhas/mês não justifica o setup)
* ❌ Não substitui dbt tests para validação no warehouse — seria redundante com dbt
* ❌ Não valida configs/settings Python — precisaria de Pydantic de qualquer forma

### Pydantic v2 + Pandera + dbt tests/contracts

Cada ferramenta na sua jurisdição: Pydantic para objetos Python, Pandera para DataFrames, dbt para warehouse.

* ✅ Validação no ponto mais precoce possível — erro detectado antes de gerar predição
* ✅ Cada ferramenta é leve e faz uma coisa bem
* ✅ ROI de carreira altíssimo: Pydantic é padrão em FastAPI, LangChain, SDKs de LLM
* ✅ Pandera já é conhecido (uso prévio em projeto Dengue-MT) — reforço sem curva
* ✅ dbt tests/contracts já são diferencial técnico do Ediney
* ❌ Três ferramentas para manter (mas cada uma é trivial no escopo usado)
* ❌ Sem "data docs" unificado (cada ferramenta reporta erro no seu formato)

### Apenas dbt tests/contracts

Validação concentrada no warehouse, usando testes SQL e contracts.

* ✅ Uma única ferramenta, já dominada pelo Ediney
* ✅ Integração nativa com o warehouse e com CI/CD
* ❌ **Validação tardia:** dado já entrou no BigQuery quando o teste roda — predição lixo já foi gerada e entregue à assistente
* ❌ Não valida configs Python (settings, paths, parâmetros)
* ❌ Não valida a planilha XLSX antes da inferência

### Validação manual (asserts + try/except)

Validação ad-hoc com código Python personalizado em cada ponto.

* ✅ Zero dependências adicionais
* ✅ Controle total sobre mensagens de erro
* ❌ Código boilerplate extenso e propenso a bugs
* ❌ Sem schema declarativo — regras dispersas pelo código, difíceis de auditar
* ❌ Nenhum valor de portfólio — não demonstra adoção de ferramentas de mercado
* ❌ Manutenção proporcional ao número de campos (escala mal)

## Mapeamento: Camada × Ferramenta × O Que Valida

| Camada | Ferramenta | O que valida | Quando roda |
|---|---|---|---|
| Configs e objetos Python | **Pydantic v2** | Settings (.env), parâmetros de modelo, outputs estruturados (SHAP), contratos de API interna | Na inicialização do app e na criação de cada objeto |
| DataFrame de entrada (XLSX) | **Pandera** | Schema da planilha: tipos, ranges, nulls, domínios categóricos, colunas obrigatórias | Imediatamente após upload, antes da inferência |
| Warehouse (Bronze→Silver→Gold) | **dbt tests + contracts** | Integridade referencial, freshness, not_null, unique, accepted_values, regras de negócio SQL | No `dbt run` / `dbt test`, pós-ingestão |

## Mais Informações

* Pydantic v2: https://docs.pydantic.dev/latest/
* Pandera: https://pandera.readthedocs.io/
* dbt tests: https://docs.getdbt.com/docs/build/data-tests
* dbt contracts: https://docs.getdbt.com/docs/collaborate/govern/model-contracts
* Decisão sobre monitoramento de drift (camada 4): ver ADR-0005 (a abrir na Fase 4)