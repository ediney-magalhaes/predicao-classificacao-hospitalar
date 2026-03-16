# Dicionário de Dados (Data Dictionary) - Classificação SUS

Este documento descreve o esquema de dados utilizado pelo pipeline de Machine Learning para a classificação de faturamento hospitalar do SUS. Ele mapeia as variáveis de entrada (features), as variáveis derivadas por engenharia de atributos e as variáveis alvo (targets).

---

## 1. Variáveis de Identificação e Controle (Não modeladas)

Estas colunas circulam pelo pipeline para fins de auditoria, cruzamento e segurança, mas **não** são entregues à Inteligência Artificial para evitar *overfitting* ou vazamento de dados (*data leakage*).

| Variável | Tipo | Descrição | Regra de Negócio / Tratamento |
| :--- | :--- | :--- | :--- |
| `ATENDIMENTO` | Numérico | Chave Primária (PK) do paciente no MV Soul. | Usado no `.drop_duplicates()` e nos *Joins*. |
| `SN_PRINCIPAL` | String | Indicador de cirurgia principal no hospital. | Filtrado exclusivamente para `'SIM'`. |

---

## 2. Variáveis de Entrada (Features do Modelo)

Estas são as 10 colunas exatas que compõem a "bandeja" do método `.predict()` dos modelos LightGBM.

| Variável | Tipo | Descrição | Tratamento / Imputação |
| :--- | :--- | :--- | :--- |
| `idade` | Inteiro | Idade do paciente no momento da admissão. | Mantido como numérico contínuo. |
| `nr_dias` | Inteiro | Tempo de permanência do paciente no hospital (dias). | Mantido como numérico contínuo. |
| `cid_entrada` | String | Código CID-10 registrado na admissão (triagem). | Sanitização de strings (upper/strip). |
| `procedimento_entrada` | String | Código do procedimento faturável de entrada. | Tratado pelo OneHotEncoder no pipeline. |
| `cid_1_principal` | String | Código CID-10 principal estabelecido na alta. | Se nulo, imputado com valor de `cid_entrada`. |
| `cirurgia` | String | Descrição médica do procedimento cirúrgico. | Se nulo ou ausente, imputado com `'DESCONHECIDO'`. |
| `sexo` | String | Gênero biológico do paciente (M / F). | Tratamento de caixa alta. |
| `medico_resp_atend` | String | Identificador do médico responsável pela alta. | Anonimização/Encoding categórico. |

---

## 3. Variáveis Derivadas (Feature Engineering v4.0)

Novas colunas injetadas no pipeline através do *Left Join* com a Tabela Oficial de Categorias CID-10. O modelo as utiliza para generalizar a família da doença.

| Variável | Tipo | Origem | Descrição | Exemplo |
| :--- | :--- | :--- | :--- | :--- |
| `CAPÍTULO BREVE` | String | Dicionário Oficial | Grande categoria anatômica ou sistêmica da doença, derivada do `cid_1_principal`. | *Doenças do Aparelho Circulatório* |
| `GRUPO` | String | Dicionário Oficial | Subcategoria clínica ou bloco do CID-10. | *Doenças Hipertensivas* |

---

## 4. Variáveis Alvo (Targets / Labels)

As saídas geradas pelos dois modelos preditivos independentes.

### 4.1. Modelo 1: Grupo SUS (`PREVISAO_GRUPO`)
Define a categoria financeira global da internação. O modelo foi treinado para classificar entre as seguintes classes principais:
* `Procedimentos clínicos`
* `Procedimentos cirúrgicos` (Pode ser forçado por Regra de Negócio de *Override*)
* `Procedimentos com finalidade diagnóstica`
* `Órteses, próteses e materiais especiais`

### 4.2. Modelo 2: Complexidade SUS (`PREVISAO_COMPLEXIDADE`)
Define o nível de recurso tecnológico e financeiro consumido pelo atendimento:
* `Média Complexidade`
* `Alta Complexidade`
* `Atenção Básica`
* `Não se Aplica`

---

## 5. Regras de Limpeza (Sanitização)
* Todas as colunas do *DataFrame* são convertidas para minúsculo (`.str.lower()`) logo após o carregamento inicial para evitar quebra de contrato (*schema drift*).
* A exclusão de duplicações nas cirurgias (`subset=['ATENDIMENTO']`) garante uma relação temporal 1:1, evitando o efeito multiplicador em *Joins* do Pandas.