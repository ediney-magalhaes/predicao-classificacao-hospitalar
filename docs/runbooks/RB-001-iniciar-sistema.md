# RB-001: Iniciar o Sistema (Terminal / .bat)

**Público-alvo:** Ediney
**Fase:** 0
**Última atualização:** 2026-08-21

## Objetivo

Ligar o sistema do zero — desde o duplo clique no `.bat` até a GUI
disponível no navegador — e resolver os problemas mais comuns de
inicialização.

## Pré-requisitos

- PC com o projeto clonado na pasta OneDrive
  (`sistema_classificacaoSUS_inteligente`)
- Ambiente virtual (`venv`) já criado e com as dependências instaladas
- Arquivo `.env` presente na raiz do projeto (salt, credenciais GCP)

## Passo a Passo

1. Navegue até a pasta raiz do projeto no Explorer
2. Dê duplo clique em `iniciar_app.bat`
3. Aguarde — o navegador abre automaticamente com a GUI Streamlit
4. Confirme que a tela de login aparece (`🔐 Acesso ao Sistema`)
5. Prossiga conforme RB-002 (gerar previsões) ou RB-003 (enviar
   correções e movimentações)

## Troubleshooting

**O navegador não abre automaticamente**
→ O terminal que abre junto com o `.bat` normalmente mostra uma URL
tipo `http://localhost:8501`. Copie e cole manualmente no navegador.

**Erro de caminho muito longo (`MAX_PATH`) ao rodar algum comando
dentro do projeto (ex: `dbt deps`, `git clean`, instalação de pacotes)**
→ Problema conhecido: a pasta do projeto vive dentro do OneDrive, com
caminho longo o suficiente para estourar o limite de 260 caracteres
do Windows em operações que criam subpastas profundas (pacotes dbt,
por exemplo). Solução: criar uma unidade virtual mais curta antes de
rodar o comando problemático:
```
subst D: "C:\Users\ediney.junior\OneDrive\Engenheiro-Cientista-Analista de dados\sistema_classificacaoSUS_inteligente"
```
Depois, navegue para `D:\` e rode o comando de lá. **Atenção:** esse
mapeamento não é persistente — precisa ser recriado a cada sessão/
reinicialização do terminal.

**O `.bat` fecha sozinho sem abrir nada**
→ Provável erro na ativação do `venv` ou dependência faltando. Abra
um terminal manualmente, ative o `venv`
(`.\venv\Scripts\Activate.ps1`) e rode `streamlit run app.py`
diretamente para ver a mensagem de erro completa.

**Tela de login não aceita a senha**
→ Confirme que `.streamlit/secrets.toml` existe e tem a senha correta
configurada. Esse arquivo não é versionado no Git — se for uma
máquina nova, precisa ser criado manualmente.

## Rollback

Não aplicável — esta é uma operação de leitura/inicialização, não
grava nem altera nenhum dado.