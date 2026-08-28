# RB-003: Upload de Correções e Movimentações Mensais

**Público-alvo:** Assistente
**Fase:** 2
**Última atualização:** 2026-08-21

## Objetivo

Enviar, todo mês, a planilha de predições já corrigida e o relatório de
movimentações do hospital, para que o sistema aprenda com as correções
e atualize os dados de passagem por UTI.

## Pré-requisitos

- Já ter gerado as predições do mês na aba "Gerar Predições" e feito o
  download da planilha
- Ter corrigido, no Excel, as colunas `PREVISAO_GRUPO` e/ou
  `PREVISAO_COMPLEXIDADE` onde o sistema errou
- Ter em mãos o relatório de movimentações do mesmo mês (arquivo
  exportado do sistema hospitalar, sem precisar de nenhum tratamento
  manual — o sistema já sabe lidar com o formato bruto)
- Acesso à GUI (`http://<IP-do-PC-do-Ediney>:8501`)

## Passo a Passo

1. Acesse a GUI e faça login com a senha de acesso
2. Clique na aba **"Enviar Correções"**
3. Selecione o **mês e ano de referência** — deve ser o mesmo mês usado
   na hora de gerar as predições
4. No campo **"Planilha revisada (com correções)"**, envie o arquivo
   Excel que você corrigiu
5. No campo **"Relatório de Movimentações"**, envie o arquivo do
   relatório de movimentações do mesmo mês — **os dois uploads são
   obrigatórios**; o botão de processar só aparece disponível quando
   ambos os arquivos estiverem carregados
6. Confira as mensagens de confirmação de carregamento
   ("Arquivos carregados: X registros de correção, Y registros de
   movimentações")
7. Clique em **"Processar Correções"**
8. Aguarde — o processamento cuida das duas informações ao mesmo
   tempo e pode levar alguns segundos
9. Confira os dois resultados na tela:
   - **Resumo das correções**: quantas linhas foram alteradas em
     Grupo e Complexidade, e a taxa de correção
   - **Resultado das movimentações**: confirmação de quantos
     registros foram enviados

## Troubleshooting

**"Faça upload da planilha revisada para continuar" não some mesmo
com os dois arquivos carregados**
→ Confira se os dois campos realmente têm um arquivo anexado (ícone
de arquivo visível, não só a área de upload vazia). Os dois são
obrigatórios juntos.

**Erro na etapa "validação" (correções)**
→ A mensagem de erro aponta a coluna com problema. Normalmente é um
valor digitado errado em `PREVISAO_GRUPO` ou `PREVISAO_COMPLEXIDADE`
que não corresponde a nenhuma das categorias válidas. Corrija no
Excel e reenvie.

**Erro na etapa "reconstrução de layout" ou "validação" (movimentações)**
→ Provavelmente o arquivo do relatório de movimentações não é o mês
certo, está corrompido, ou o sistema hospitalar mudou o formato de
exportação. Avise o Ediney com a mensagem de erro completa.

**Erro na etapa "ingestão" (qualquer um dos dois)**
→ Problema de conexão com o BigQuery. Verifique a internet do PC.
Se persistir, avise o Ediney.

## Rollback

Se enviar o mês errado ou um arquivo errado por engano: **basta
reenviar o mês e os arquivos corretos**. O sistema substitui
automaticamente os dados daquele mês — não duplica nem deixa dado
antigo misturado. Não precisa fazer nada manual antes de reenviar.