# RB-004: Enviar o Financeiro Mensal (Qlik → Bronze)

**Público-alvo:** Ediney
**Fase:** 3
**Última atualização:** 2026-11-23

## Objetivo

Extrair, todo mês, o relatório de contas hospitalares do Qlik e enviá-lo
pela aba "Financeiro" da GUI, para alimentar a tabela
`bronze_financeiro_anonimizado` (base do `mart_financeiro`).

## Pré-requisitos

- Acesso à GUI (`http://<IP-do-PC-do-Ediney>:8501`)
- Acesso ao QlikView do hospital
- O mês anterior já enviado (veja "Regra de ouro")

## Como gerar o relatório

Relatório: **HSR - Análise de Contas** (QlikView).

| Campo | Valor |
|---|---|
| Filtro "Final Conta" | o **mês de referência**, um mês por extração |

Salve em Excel (.xlsx), **excluindo a linha de totais - linha 2 abaixo do cabeçalho**, com o nome
`mes_ano.xlsx` (ex.: `outubro_2026.xlsx`) na pasta `Banco de dados/Contas`
do W:.

**Regra de ouro: nunca pule um mês.** Cada extração captura as contas
cujo fechamento caiu naquele mês. Se um mês for pulado, as contas dele
nunca entram na Bronze por outra extração. Se acontecer, extraia o mês
perdido retroativamente antes de seguir (ADR-0004, atualização de
2026-09-25).

Colunas que o relatório precisa ter (se faltar alguma, o envio falha):

`NR_ATENDIMENTO`, `NR_INTERNO_CONTA`, `MES_ANO_PRODUCAO`, `ANO_PRODUCAO`,
`VALOR`, `CONVENIO`, `PACIENTE`, `VALOR RECEBIDO`, `VALOR GLOSA`

`MES_ANO_PRODUCAO` precisa vir no formato `out 2026` (3 letras
minúsculas, espaço e ano).

## Passo a Passo

1. Acesse a GUI e faça login
2. Clique na aba **"💰 Financeiro"**
3. No campo **"Relatório Análise de Contas"**, envie o arquivo do mês
4. Confira a mensagem "Arquivo carregado: X registros das contas
   hospitalares"
5. Clique em **"Processar Financeiro"**
6. Confira o resultado: "Dados financeiros processados com sucesso. X
   registros enviados para a Bronze". X deve ser igual ao número de
   linhas do arquivo

## Conferência (recomendada)

Compare a Bronze com o arquivo. No BigQuery:

```sql
SELECT
  COUNT(*)            AS linhas,
  SUM(valor)          AS soma_valor,
  SUM(valor_recebido) AS soma_recebido,
  SUM(valor_glosa)    AS soma_glosa
FROM `ml-classificacao-sus.dados_saidas_hospitalares.bronze_financeiro_anonimizado`
WHERE data_ingestao = (
  SELECT MAX(data_ingestao)
  FROM `ml-classificacao-sus.dados_saidas_hospitalares.bronze_financeiro_anonimizado`
)
```

No Excel, some as colunas `VALOR`, `VALOR RECEBIDO` e `VALOR GLOSA` (barra
de status). A contagem e as três somas devem bater centavo por centavo.
Não filtre por `mes_ano_producao`: o arquivo pode trazer contas com
produção em meses anteriores.

Observação: em meses recém-fechados, `VALOR RECEBIDO` e `VALOR GLOSA`
vêm muito pequenos perto de `VALOR` (outubro/2026: R$ 13.223,62 e
R$ 130,86 contra R$ 14.464.875,93 de faturamento). Isso vem do próprio
Qlik, não é erro do pipeline.

## Troubleshooting

**Erro na etapa "validação"**
→ A mensagem lista, para cada problema, a coluna, a verificação que
falhou e o valor. Corrija no arquivo e reenvie.

**Erro de coluna ausente**
→ Confira se o relatório do Qlik tem as 9 colunas listadas acima, com
os cabeçalhos exatos.

**Erro na etapa "envio"**
→ Problema de conexão com o BigQuery. Verifique a internet e as
credenciais; se persistir, olhe o log da GUI.

## Rollback

O envio é um MERGE com chave `NR_INTERNO_CONTA` + `MES_ANO_PRODUCAO`:
reenviar o mesmo arquivo **não duplica**, só atualiza as contas já
existentes e insere as novas. Para corrigir um envio errado, reenvie o
arquivo correto.

Limite do MERGE: ele não remove. Uma conta que existia na Bronze e
**não** está mais no arquivo reenviado continua lá.