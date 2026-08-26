# RB-002: Gerar Previsões Mensais (Streamlit)

**Público-alvo:** Assistente
**Fase:** 1
**Última atualização:** 2026-08-21

## Objetivo

Fazer upload das 3 planilhas mensais e gerar as predições de Grupo e
Complexidade SUS para todos os atendimentos do mês.

## Pré-requisitos

- Acesso à GUI (`http://<IP-do-PC-do-Ediney>:8501`)
- As 3 planilhas do mês, extraídas dos sistemas de origem:
  - Planilha de Saídas (Epidemio)
  - Planilha de Altas (Sistema MV)
  - Planilha de Cirurgias Realizadas

## Passo a Passo

1. Acesse a GUI e faça login com a senha de acesso
2. Na aba **"Gerar Predições"**, selecione o **mês e ano de referência**
3. Faça upload das 3 planilhas, cada uma no campo correspondente:
   "Planilha de Saídas", "Altas do Sistema MV", "Cirurgias Realizadas"
4. Confira a seção **"Validação dos dados"**, cada planilha deve
   aparecer com um check verde e o número de registros válidos. Se
   alguma aparecer com erro (vermelho), veja o Troubleshooting abaixo
5. Com as 3 validadas, clique em **"Gerar Predições"**
6. Aguarde o processamento (pode levar alguns segundos)
7. Confira a seção **"Resultado"**:
   - **Alertas** (topo): duplicados removidos, atendimentos de outro
     hospital removidos, atendimentos que constam no MV mas não na
     planilha de Saídas (precisam ser buscados manualmente e
     adicionados antes da etapa de correção)
   - **Métricas**: registros processados, overrides aplicados, e
     quantos casos têm baixa confiança (merecem atenção redobrada na
     revisão)
   - **Distribuição das predições**: quantos atendimentos caíram em
     cada categoria de Grupo e Complexidade
8. Clique em **"Baixar planilha com predições"**, o arquivo já vem
   com as colunas de predição e confiança prontas para revisão no Excel

## Troubleshooting

**Uma das planilhas aparece com erro (❌) na validação**
→ A mensagem indica qual coluna está com problema (faltando, tipo
errado, ou fora do intervalo esperado). Confira a planilha de origem,
corrija e faça o upload novamente.

**Aparece um aviso de "atendimentos para buscar no MV"**
→ Esses atendimentos não seguem para a predição até serem localizados
e adicionados manualmente na planilha de Saídas. Busque cada número
de atendimento no sistema, adicione a linha correspondente, e refaça
o upload da planilha de Saídas.

**Erro durante o processamento (após clicar em "Gerar Predições")**
→ Anote a mensagem de erro completa e avise o Ediney, normalmente
indica um problema no arquivo (formato inesperado) que precisa de
investigação técnica.

## Rollback

Não há ação destrutiva nesta etapa, gerar predições não grava nada
na Bronze nem altera dado permanente. Se algo sair errado, é só
recomeçar o upload das planilhas.