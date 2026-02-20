# 🏥 Sistema Analítico Preditivo para Classificação Hospitalar (MLOps Edition)

**Analytics Engineering + Machine Learning aplicado à gestão hospitalar**

## 🎯 Contexto de Negócio

Hospitais precisam classificar internações por:
* **Grupo Assistencial (GRUPO_SUS)** — clínico, cirúrgico, diagnóstico, etc.
* **Complexidade Assistencial (COMPLEXIDADE_SUS)** — baixa, média ou alta complexidade.

Historicamente, esse processo exigia a leitura manual de ~900 prontuários/mês, levando cerca de 10 dias de trabalho humano exclusivo.

## 🚀 Transformação Implementada (Arquitetura MLOps)

O projeto evoluiu de scripts manuais em notebooks para um pipeline de produção automatizado, robusto e em conformidade com a LGPD.

**Principais Impactos:**
* **Redução de Carga Operacional:** De 10 dias para 20-30 minutos.
* **Conformidade LGPD:** Anonimização automática de dados sensíveis antes da nuvem.
* **Escalabilidade:** Integração nativa com Data Warehouse em nuvem (Google BigQuery).
* **Confiabilidade:** Separação entre Ingestão, Pré-processamento e Modelagem.

## 🧭 Jornada do Dado (End-to-End)

**1️⃣ Extração e Ingestão Automática**
* Carregamento de bases extraídas do sistema Soul MV.
* **Limpeza de Schema:** Padronização de nomes de colunas (Snake Case) via Regex para compatibilidade analítica.

**2️⃣ Blindagem de Dados (LGPD)**
* **Criptografia:** Anonimização de nomes e CPFs utilizando SHA-256 com "Salt" secreto.
* **Segurança de Infraestrutura:** Uso de variáveis de ambiente (`.env`) e autenticação via Service Accounts do GCP.

**3️⃣ Armazenamento em Nuvem (Cloud Data Warehouse)**
* Ingestão automatizada para o Google BigQuery.
* Centralização do histórico hospitalar para treinamento de modelos globais.

**4️⃣ Pré-processamento e Limpeza Clínica**
* **Mitigação de Data Drift:** Filtro temporal automático (Janela pós-2020).
* **Qualidade de Dados:** Remoção de Nulos e tratamento de classes raras (< 10 amostras).
* **Engenharia de Features:** Extração automática de capítulos do CID.

**5️⃣ Modelagem e Inteligência Artificial (Pipeline de Treinamento)**
* **Tradução Matemática:** Uso de `ColumnTransformer` (Scikit-Learn) para escalonamento de features numéricas (`StandardScaler`) e codificação de textos (`OneHotEncoder`).
* **Prevenção de Viés:** Balanceamento dinâmico via **SMOTE** implementado apenas na fase de treino para evitar vazamento de dados (*Data Leakage*).
* **Treinamento Duplo:** Modelagem simultânea para Grupo e Complexidade utilizando **LightGBM**.
* **Serialização:** Geração de artefatos de modelo (`.joblib`) para separação total entre ambiente de Treino e Inferência (Predição em tempo real).

## 📊 Resultados e Performance (Baseline)

| Métrica | Resultado |
| :--- | :--- |
| **Acurácia COMPLEXIDADE** | 96% |
| **Acurácia GRUPO_SUS** | 95% |
| **Redução de Esforço Manual** | ~95% |
| **Tempo de Processamento** | < 1 min |

## 🧠 Decisões Técnicas Relevantes (MLOps)

* **Modularização:** Código separado em `ingestion`, `preprocessing` e `modelagem` para facilitar a manutenção.
* **Ambientes Isolados:** Uso de VENV e `requirements.txt` para reprodutibilidade.
* **Segurança:** Bloqueio total de chaves e dados no histórico do Git via `.gitignore`.
* **Governança:** Separação clara entre dados brutos (Raw), dados anonimizados (Trusted) e a camada de entrega da IA.

## 🛠 Tecnologias Utilizadas

* **Linguagem:** Python 3.11+
* **Processamento:** Pandas, Google Cloud BigQuery API (`pandas-gbq`)
* **Segurança:** Hashlib, Dotenv, OAuth2
* **IA/ML:** Scikit-learn, LightGBM, Imbalanced-learn (SMOTE), Joblib
* **Infraestrutura:** Google Cloud Platform (GCP)

## 🚀 Próximos Passos

* [x] Finalizar módulo de Treinamento automatizado e serialização de modelos.
* [ ] **Desenvolver API de predição em tempo real (FastAPI/Flask) para consumo dos modelos gerados.**
* [ ] Implementar Regras de Negócio de *Override* (Cirurgias x Clínicos).
* [ ] Criar Dashboard executivo no Looker Studio conectado ao BigQuery.
* [ ] Containerização via Docker.

---
*Desenvolvido por Ediney Magalhães | Analytics Engineering | Machine Learning Aplicado | Healthcare Data*