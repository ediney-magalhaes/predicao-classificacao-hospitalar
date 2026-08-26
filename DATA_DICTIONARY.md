# Dicionário de Dados (Data Dictionary) - Classificação SUS

Este documento descreve o esquema de dados utilizado pelo pipeline de Machine Learning para a classificação de faturamento hospitalar do SUS. Ele mapeia as variáveis de entrada (features), as variáveis derivadas por engenharia de atributos, as variáveis de saída (predições e confiança) e as regras de tratamento aplicadas.

As listas de features por modelo são configuráveis em `config/settings.py` (`features_grupo` e `features_complexidade`), evitando hardcoding no pipeline.

---

## 1. Variáveis de Identificação e Controle (Não modeladas)

Estas colunas circulam pelo pipeline para fins de auditoria, cruzamento e segurança, mas **não** são entregues à Inteligência Artificial para evitar *overfitting* ou vazamento de dados (*data leakage*).

| Variável | Tipo | Descrição | Regra de Negócio / Tratamento |
| :--- | :--- | :--- | :--- |
| `ATENDIMENTO` | Numérico | Chave Primária (PK) do paciente no MV Soul. | Usado no `.drop_duplicates()`, nos *Joins* e na validação cruzada com altas do MV. |
| `SN_PRINCIPAL` | String | Indicador de cirurgia principal no hospital. | Filtrado exclusivamente para `'SIM'` na planilha de cirurgias. |
| `COD_CID_SUMARIO` | String | CID registrado no sumário de alta. | Removida no pipeline (não usada pelo modelo). |

---

## 2. Variáveis de Entrada (Features do Modelo)

Os dois modelos LightGBM utilizam 10 features cada. São 8 variáveis originais das planilhas + 2 variáveis derivadas por feature engineering (seção 3). A ordem das features é preservada conforme o treino e está definida em `config/settings.py`.

| Variável | Tipo | Descrição | Tratamento / Imputação |
| :--- | :--- | :--- | :--- |
| `idade` | Inteiro | Idade do paciente no momento da admissão. | Mantido como numérico contínuo. Validação Pandera: 0-130. |
| `nr_dias` | Inteiro | Tempo de permanência do paciente no hospital (dias). | Mantido como numérico contínuo. Validação Pandera: ≥ 0. |
| `cid_entrada` | String | Código CID-10 registrado na admissão (triagem). | Sanitização de strings (`upper`/`strip`) no merge com dicionário. |
| `procedimento_entrada` | String | Código do procedimento faturável de entrada. | Tratado pelo OneHotEncoder no pipeline de treino. |
| `cid_1_principal` | String | Código CID-10 principal estabelecido na alta. | Se nulo, imputado com valor de `cid_entrada`. Sanitização (`upper`/`strip`). |
| `cirurgia` | String | Descrição do procedimento cirúrgico realizado. | Se nulo ou ausente, imputado com `'DESCONHECIDO'`. Usado também no Business Rule Override. |
| `sexo` | String | Sexo biológico do paciente (M / F). | Tratamento de caixa alta. |
| `medico_resp_atend` | String | Identificador do médico responsável pelo atendimento. | Anonimização/encoding categórico. |

---

## 3. Variáveis Derivadas (Feature Engineering)

Colunas injetadas no pipeline através de *Left Join* com o Dicionário Oficial de Categorias CID-10 (`data/Categorias de CIDs.xlsx`). O modelo as utiliza para generalizar a família da doença, melhorando a capacidade de predição em CIDs raros.

A lógica reside em `src/preprocessing/preparo_ml.py` (função `engenharia_features`). O caminho do dicionário é configurável via `settings.dicionario_cid_path`.

| Variável | Tipo | Origem | Descrição | Exemplo |
| :--- | :--- | :--- | :--- | :--- |
| `CAPÍTULO BREVE` | String | Dicionário Oficial CID-10 | Grande categoria anatômica ou sistêmica da doença, derivada do `cid_1_principal`. | *Doenças do Aparelho Circulatório* |
| `GRUPO` | String | Dicionário Oficial CID-10 | Subcategoria clínica ou bloco do CID-10. | *Doenças Hipertensivas* |

---

## 4. Variáveis de Saída (Predições e Confiança)

### 4.1. Modelo 1: Grupo SUS (`PREVISAO_GRUPO`)
Define a categoria financeira global da internação. Classes:
* `Procedimentos clínicos`
* `Procedimentos cirúrgicos` (pode ser forçado pelo Business Rule Override)
* `Procedimentos com finalidade diagnóstica`
* `Órteses, próteses e materiais especiais`

### 4.2. Modelo 2: Complexidade SUS (`PREVISAO_COMPLEXIDADE`)
Define o nível de recurso tecnológico e financeiro consumido pelo atendimento. Classes:
* `Média Complexidade`
* `Alta Complexidade`
* `Atenção Básica`
* `Não se Aplica`

### 4.3. Scores de Confiança
Cada predição acompanha um score de confiança calculado como `max(predict_proba)` do modelo.

| Variável | Tipo | Range | Descrição |
| :--- | :--- | :--- | :--- |
| `CONFIANCA_GRUPO` | Float | 0.0 - 1.0 | Confiança do modelo na predição de GRUPO_SUS. |
| `CONFIANCA_COMPLEXIDADE` | Float | 0.0 - 1.0 | Confiança do modelo na predição de COMPLEXIDADE_SUS. |

Valores abaixo de 0.7 são sinalizados como "baixa confiança" na GUI, indicando que a assistente deve revisar com atenção especial.

**Nota sobre calibração:** os scores de confiança atuais indicam confiança relativa, não probabilidade calibrada. Na Fase 6 (ADR-0009), calibração por isotonic regression fará com que um score de 0.8 signifique efetivamente 80% de chance de acerto.

### 4.4. Persistência na Bronze (pós-HITL)

Após a revisão humana, `PREVISAO_GRUPO` e `PREVISAO_COMPLEXIDADE` (a predição bruta do modelo) são preservadas na Bronze como `previsao_grupo` e `previsao_complexidade`, colunas distintas de `grupo_sus`/`complexidade_sus`
(o valor final, já corrigido pela assistente). Essa distinção existe para permitir cálculo de Precision/Recall pós-revisão e análise de transições de erro (o que o modelo previu vs. o que foi corrigido), sem confundir
predição com gabarito. Implementado em `src/hitl/pipeline_correcao.py` via merge com a predição original salva na W: antes do rename para os nomes finais da Bronze.

---

## 5. Regras de Tratamento e Limpeza

### 5.1. Normalização de Colunas
Todas as colunas do DataFrame são convertidas para minúsculo (`.str.lower()`) **antes** do merge com o dicionário de CIDs. Isso garante que as colunas originais do hospital fiquem em lowercase, enquanto as colunas adicionadas pelo dicionário (`CAPÍTULO BREVE`, `GRUPO`) mantêm seus nomes em maiúsculo — exatamente como o modelo espera.

### 5.2. Deduplicação
- **Planilha de saídas:** `drop_duplicates(subset=['ATENDIMENTO'])` antes de qualquer processamento.
- **Planilha de cirurgias:** `drop_duplicates(subset=['ATENDIMENTO'])` após filtro de `SN_PRINCIPAL == 'SIM'`, garantindo relação 1:1 e evitando efeito multiplicador no merge.

### 5.3. Validação Cruzada com Altas do MV
Atendimentos presentes na planilha de saídas mas ausentes na lista de altas do MV são removidos (intrusos de outro hospital). Atendimentos presentes no MV mas ausentes na planilha de saídas geram alerta.

### 5.4. Imputação
- `CID_1_PRINCIPAL`: quando nulo, preenchido com `CID_ENTRADA` (fallback).
- `cirurgia`: quando nulo (paciente não operado), preenchido com `'DESCONHECIDO'`.

### 5.5. Sanitização de Chaves de Cruzamento
Antes do merge com o dicionário CID-10, tanto `cid_1_principal` (DataFrame) quanto `CÓDIGO CID` (dicionário) passam por `.astype(str).str.upper().str.strip()` para eliminar inconsistências de caixa e espaços invisíveis.

### 5.6. Business Rule Override
Regra de negócio que corrige predições do modelo GRUPO_SUS onde a IA classificou como "Procedimentos clínicos" mas o paciente possui registro de cirurgia realizada (coluna `cirurgia` não está na lista de valores não-cirúrgicos). A correção força a classe para "Procedimentos cirúrgicos". Valores e classes configuráveis em `settings.py`.

---

## 6. Validação de Schema (Pandera)

As 3 planilhas de entrada são validadas com Pandera antes de entrar no pipeline. Os schemas estão definidos em `src/validacao/validacao.py`.

| Planilha | Schema | Validação |
| :--- | :--- | :--- |
| Saídas (Epidemio) | `schema_saidas` | Colunas obrigatórias, tipos, ranges (idade 0-130, nr_dias ≥ 0) |
| Altas do MV | `schema_altas` | Validação mínima por posição (cabeçalhos imprevisíveis do MV) |
| Cirurgias | `schema_cirurgias` | 3 colunas obrigatórias: ATENDIMENTO, SN_PRINCIPAL, DESCRICAO_CIRURGIA |

As listas de colunas obrigatórias são mantidas em `config/settings.py`, evitando duplicação entre código e documentação.

**Nota:** Existe uma 4ª fonte de dados, o relatório de movimentações internas (usado para reconstruir passagem por UTI, ver `mart_uti`), validado por `schema_movimentacoes` em `src/validacao/schemas_movimentacoes.py`.
Diferente das 3 planilhas acima, não alimenta o modelo, é ingestão direta para a Bronze(`bronze_movimentacoes_anonimizado`), sem passar pelo pipeline de predição.