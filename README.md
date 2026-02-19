# Sistema de Classificação SUS Inteligente (MLOps)

Este projeto automatiza a ingestão, anonimização e classificação de dados hospitalares para o SUS, utilizando uma arquitetura escalável e segura.

## 🛠️ O que foi implementado até agora:

### 1. Pipeline de Ingestão e Blindagem (LGPD)
* **Anonimização:** Criptografia SHA-256 com "Salt" em variáveis sensíveis (Nome, CPF).
* **Limpeza de Schema:** Padronização automática de cabeçalhos (Snake Case) para compatibilidade com Data Warehouses.
* **Segurança:** Uso de variáveis de ambiente (`.env`) para proteger chaves e segredos.

### 2. Infraestrutura em Nuvem (GCP)
* **BigQuery:** Integração direta via Python para armazenamento analítico.
* **Service Account:** Autenticação via conta de serviço para execução automatizada.

### 3. Pré-processamento Clínico
* **Filtros:** Seleção de dados por janela temporal (Ano >= 2020).
* **Qualidade:** Remoção automática de registros nulos e classes raras (min_samples).
* **Feature Engineering:** Extração automática de capítulos de CID.

## 🚀 Como Executar

1. Certifique-se de que o seu `.env` contém as chaves `SALT_SUS`, `GCP_PROJECT_ID` e `GOOGLE_APPLICATION_CREDENTIALS`.
2. Ative o ambiente virtual: `.\venv\Scripts\activate`
3. Execute o orquestrador principal: `python main.py`