# Arquitetura do Sistema Preditivo - Classificação SUS

Este documento detalha o desenho arquitetural do pipeline de dados, a infraestrutura em nuvem, os protocolos de segurança e o ciclo de vida de Machine Learning (MLOps) aplicados no projeto.

---

## 1. Visão Geral do Pipeline (End-to-End)

O sistema foi desenhado para processar dados de internações hospitalares (On-Premise), aplicar modelos preditivos de Inteligência Artificial e retroalimentar um Data Warehouse na nuvem para consumo analítico. O fluxo divide-se em duas frentes principais: **Inferência Lote (Batch)** e **Retreinamento Contínuo**.

### 1.1. Ingestão e Processamento (Inferência Mensal)
1. **Extração:** Arquivos brutos gerados pelo sistema MV Soul (Altas e Cirurgias Realizadas) alimentam o pipeline local.
2. **Sanitização:** O script realiza desduplicação (ex: tratamento da "Armadilha do PROCV" em cirurgias múltiplas) e aplica um filtro de exclusão (`.isin()`) para remover pacientes de outras unidades hospitalares.
3. **Feature Engineering (Mapeamento Semântico):** A primeira via de diagnóstico (CID-10) sofre um *Left Join* com o Dicionário Oficial do SUS, injetando as variáveis categóricas `CAPÍTULO BREVE` e `GRUPO` para enriquecer a capacidade de generalização do modelo.
4. **Predição:** Os dados são vetorizados e submetidos a dois modelos `LightGBM` independentes (Grupo SUS e Complexidade).
5. **Business Rule Override:** Uma trava de segurança baseada em regras de negócio corrige falsos positivos da IA (ex: predição de "Procedimento Clínico" alterada compulsoriamente para "Cirúrgico" se houver registro de código cirúrgico faturado).

---

## 2. Arquitetura Medallion "Zero Cost" (Google BigQuery)

Para garantir governança dos dados históricos e disponibilização estruturada para o Power BI com **custo de infraestrutura zero**, o sistema utiliza o Free Tier do Google Cloud (GCP) com uma abordagem Medallion Lógica (focada em Views em vez de Tabelas físicas).

* **🥉 Camada Bronze (Raw / Histórico Validado):** * **Tipo:** Tabela Física (`storage`).
  * **Função:** Única fonte de verdade (*Single Source of Truth*). Recebe exclusivamente os dados via *append* mensal após a validação humana (Human-in-the-loop). 
* **🥈 Camada Silver (Standardized / Enriched):**
  * **Tipo:** View SQL Lógica (`compute-only`).
  * **Função:** Limpeza padronizada (tipagem de datas, tratamento de *nulls*, padronização de nomenclatura). Custo de armazenamento zero. Garante que qualquer alteração de regra de limpeza não afete o dado bruto.
* **🥇 Camada Gold (Aggregated / Business-Ready):**
  * **Tipo:** View SQL Lógica (`compute-only`).
  * **Função:** Agregações específicas para consumo do Power BI (ex: volumetria de complexidade por mês, faturamento projetado, giro de leito). Totalmente desacoplada do pipeline de ML.

---

## 3. Estrutura MLOps e Ciclo de Vida

O projeto separa estritamente o código de inferência do código de treinamento para evitar contaminação e *data leakage*.

* **Treinamento (`executar_treino.py`):**
  * Conecta-se diretamente à Camada Bronze do BigQuery.
  * Utiliza `ImbPipeline` para garantir que o balanceamento sintético de classes (SMOTE) ocorra *apenas* nos dados de treino durante a validação cruzada.
  * Serializa os hiperparâmetros e os artefatos de modelo via `joblib`.
  * Filtro de Data Drift: O treinamento utiliza apenas dados a partir de 2020 para refletir o perfil assistencial contemporâneo.
* **Human-in-the-loop (Feedback Loop):**
  * A IA atua como um sistema de suporte à decisão (Copilot). A saída do modelo passa por validação de um operador humano (Governança Clínica). As correções manuais são injetadas na Camada Bronze, forçando o modelo a aprender com as correções nas próximas execuções de retreinamento.

---

## 4. Segurança, Privacidade e LGPD

Tratando-se de dados sensíveis de saúde (PHI), a arquitetura incorpora camadas de proteção por padrão (*Privacy by Design*):

1. **Anonimização Criptográfica:** Nomes de pacientes e CPFs nunca são enviados à nuvem em texto plano. O pipeline local aplica *hashing* irreversível `SHA-256` combinado com um `Salt` criptográfico aleatório (injetado via variável de ambiente).
2. **Gerenciamento de Segredos:** O `Salt` criptográfico e os caminhos dos arquivos do Google credentials não residem no código fonte, sendo gerenciados estritamente via arquivo `.env` (excluído do versionamento via `.gitignore`).
3. **Autenticação Cloud:** Acesso ao BigQuery ocorre estritamente via Service Accounts do GCP com políticas de privilégio mínimo (IAM), sem uso de contas de usuário pessoal.

---

## 5. Stack Tecnológica Base
* **Core:** Python 3.12, Pandas, Scikit-Learn
* **Machine Learning:** LightGBM, Imbalanced-Learn (SMOTE)
* **Data Warehouse:** Google BigQuery (Standard SQL)
* **Versionamento & Ambiente:** Git, GitHub, venv, python-dotenv