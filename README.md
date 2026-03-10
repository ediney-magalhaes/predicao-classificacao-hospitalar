# Sistema Analítico Preditivo para Classificação Hospitalar (MLOps Edition)

**Status:** Em Produção | **Linguagem:** Python 3.12 | **Modelagem:** LightGBM + SMOTE

## Contexto do Problema e Impacto no Negócio
Hospitais lidam com um volume massivo de dados de internações que precisam ser rigorosamente classificados para fins de faturamento e auditoria. As duas principais classificações exigidas são:
* **Grupo Assistencial (GRUPO_SUS):** Clínico, Cirúrgico, Diagnóstico, Órteses e Próteses, etc.
* **Complexidade Assistencial (COMPLEXIDADE_SUS):** Baixa, Média ou Alta complexidade.

**O Problema (Antes):** Historicamente, este processo exigia a leitura manual de aproximadamente 900 prontuários por mês, consumindo cerca de 40 dias de trabalho humano exclusivo, com margem para erros de digitação e inconsistências de interpretação.

**A Solução (Depois):** Implementação de um pipeline de Machine Learning e Engenharia de Dados ponta a ponta. O tempo de processamento caiu de ~40 dias para menos de 1 minuto, garantindo consistência algorítmica, mitigando glosas médicas (recusas de pagamento) e garantindo conformidade total com a LGPD.

## Métricas de Impacto e Evolução de Performance

O acompanhamento de métricas é realizado continuamente para monitorar *Data Drift* e a degradação do modelo. Abaixo, a evolução em dados de validação reais nos últimos meses de operação:

| Métrica | Novembro/2025 | Dezembro/2025 | Janeiro/2026 (Atual) | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Acurácia (Complexidade)** | 96% | 96% | **95%** | Estável |
| **F1-Score (Alta Complexidade)** | 0.85 | 0.86 | **0.85** | Estável |
| **Acurácia (Grupo SUS)** | 95% | 95% | **95%** | Estável |
| **F1-Score (Órteses e Próteses)** | 0.62 | 0.72 | **0.77** | Melhora Contínua |

*Nota: A evolução expressiva de F1-Score na classe minoritária de "Órteses e Próteses" reflete o ajuste fino do pipeline de balanceamento (SMOTE) no pré-processamento.*

## Arquitetura e Jornada do Dado (End-to-End)

O projeto ultrapassa a modelagem isolada, estabelecendo um fluxo completo de ETL, Governança, Modelagem e Inferência.

### 1. Extração, Limpeza e Integração (ETL)
* **Ingestão Automatizada:** Carregamento de bases extraídas do sistema transacional (Soul MV) contendo dados de Saídas e Cirurgias.
* **Padronização de Schema:** Normalização de colunas (Snake Case, Lowercase) via Expressões Regulares (Regex), garantindo compatibilidade entre as tabelas do sistema legado e o ambiente analítico.
* **Auditoria de Dados:** O script de inferência valida automaticamente a integridade das planilhas, cruzando os atendimentos processados contra as altas registradas no sistema MV, alertando a operação sobre prontuários faltantes.

### 2. Governança e Blindagem de Dados (LGPD)
* **Anonimização Criptográfica:** Nomes de pacientes e CPFs são anonimizados utilizando algoritmo SHA-256 com "Salt" secreto antes de qualquer tráfego em rede.
* **Segurança de Infraestrutura:** Autenticação no Cloud Data Warehouse via Service Accounts do Google Cloud Platform (GCP) e credenciais isoladas em variáveis de ambiente (`.env`).

### 3. Armazenamento e Modelagem de Dados (Cloud Data Warehouse)
* **Carga (Load):** Ingestão dos dados anonimizados para o Google BigQuery (`pandas-gbq`).
* **Modelagem SQL:** Centralização do histórico hospitalar em tabelas estruturadas, permitindo consultas legíveis e servindo como fonte única da verdade (Single Source of Truth) para o treinamento de modelos globais.

### 4. Pré-processamento e Feature Engineering
* **Mitigação de Data Drift:** Filtro temporal implementado via código para treinar os modelos exclusivamente com dados de 2020 em diante, refletindo os protocolos médicos atuais.
* **Tratamento de Anomalias:** Remoção de valores nulos críticos e supressão de classes estatisticamente irrelevantes (menos de 10 amostras).
* **Engenharia de Features:** Extração inteligente, como a derivação automática do Capítulo do CID a partir do código primário (`str[0]`).
* **Relacionamento de Tabelas:** Execução de *Left Joins* otimizados, selecionando estritamente chaves primárias e colunas-alvo para evitar colisão de variáveis (`_x` / `_y`) durante o cruzamento entre base de pacientes e base cirúrgica.

### 5. Modelagem e Inteligência Artificial (MLOps)
O pipeline foi separado em dois módulos isolados para garantir estabilidade em produção:

* **Módulo de Treinamento (`executar_treino.py`):**
  * Uso de `ColumnTransformer` (Scikit-Learn) para escalonamento numérico (`StandardScaler`) e codificação categórica (`OneHotEncoder`).
  * Balanceamento dinâmico via `SMOTE` aplicado estritamente na base de treino (evitando *Data Leakage*).
  * Treinamento de múltiplos algoritmos `LightGBM` (Grupo e Complexidade).
  * Geração automatizada de relatórios textuais de performance e serialização dos artefatos matemáticos (`.joblib`).

* **Módulo de Inferência (`gerar_previsoes.py`):**
  * Carregamento em memória dos modelos pré-treinados para latência sub-segundo.
  * Ingestão dos dados do mês corrente e execução de matriz de predições.

### 6. Business Rule Override (Regras de Negócio)
A IA atua como ferramenta de suporte, mas as regras de faturamento têm a palavra final. O sistema implementa uma trava de segurança algorítmica:
* Se o modelo prever "Procedimentos Clínicos", mas o sistema detectar a descrição de uma cirurgia realizada na ficha do paciente, o algoritmo realiza um *override*, forçando a classificação para "Procedimentos Cirúrgicos". Isso evita prejuízos financeiros diretos por subfaturamento.

## Decisões Técnicas e Maturidade Profissional
* **Modularização:** Repositório estruturado com separação clara de responsabilidades (Ingestion, Preprocessing, Modeling, Inference).
* **Reprodutibilidade:** Gerenciamento de dependências estrito através de ambientes virtuais (VENV) e arquivo `requirements.txt`.
* **Versionamento e Segurança:** Bloqueio de arquivos sensíveis (chaves GCP, planilhas de pacientes) no Git através do `.gitignore`.

## Tecnologias Utilizadas
* **Linguagem:** Python 3.12
* **Manipulação de Dados:** Pandas
* **Integração Cloud:** Google Cloud BigQuery API (`pandas-gbq`), OAuth2
* **Segurança:** Hashlib (SHA-256), Python-dotenv
* **Machine Learning:** Scikit-Learn, LightGBM, Imbalanced-learn (SMOTE)
* **Persistência e Deploy:** Joblib

## Próximos Passos (Roadmap Analítico)
- [ ] Construir uma API RESTful (FastAPI) para consumo dos modelos de predição em tempo real.
- [ ] Desenvolver um Dashboard Executivo no Looker Studio conectado diretamente ao BigQuery, atrelando as métricas preditivas ao planejamento financeiro do hospital.
- [ ] Containerizar a aplicação (Docker) para simplificar rotinas de deploy e agendamento contínuo (Airflow/Cron).
- [ ] Implementar suíte de testes unitários (PyTest) para as funções de limpeza e engenharia de features.

---
*Desenvolvido por Ediney Magalhães | Analytics Engineering | Machine Learning Aplicado | Healthcare Data*