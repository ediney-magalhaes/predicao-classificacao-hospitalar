# ADR-0002: Hospedar GUI Streamlit localmente no PC do hospital

> No contexto da interface de predição para a assistente não-técnica, enfrentando restrições de firewall hospitalar, proibição de tráfego de dados na internet pública e impossibilidade de instalar Docker, decidimos por hospedar o Streamlit localmente no PC do Ediney dentro da rede do hospital e descartamos Streamlit Community Cloud, Hugging Face Spaces e Docker local, para alcançar deploy imediato sem dependência da TI e com dados 100% na rede interna, aceitando que a disponibilidade depende do PC estar ligado e do app rodando durante o horário comercial.

## Status

**Aceita**

**Data:** 2026-05-15

**Decisor(es):** Ediney Magalhães

## Contexto e Problema

A assistente da equipe depende do Ediney para rodar predições via terminal. Precisa de uma GUI web onde ela faça upload da planilha XLSX, visualize as predições e baixe o resultado. O ambiente hospitalar impõe restrições severas:

* Firewall corporativo bloqueia domínios externos não autorizados
* TI não libera instalação de certos softwares (Node.js, provavelmente Docker)
* Dados de internação não devem transitar pela internet pública (compliance + política interna)
* Python com venv funciona no PC do hospital — é a exceção disponível
* A assistente só usa a interface durante o horário comercial, quando Ediney está presente

## Drivers da Decisão

* **Restrição de rede:** firewall hospitalar bloqueia domínios desconhecidos — serviços cloud provavelmente inacessíveis
* **Privacidade dos dados:** mesmo anonimizados, tráfego externo de dados hospitalares é risco político e de compliance
* **Custo:** R$ 0,00 — meta inegociável
* **Simplicidade:** 1 usuária, ~900 linhas/mês, 1 uso mensal — solução deve ser proporcional ao problema
* **Independência da TI:** quanto menos precisar pedir liberação, melhor

## Opções Consideradas

1. Streamlit local no PC do hospital (rede interna)
2. Streamlit Community Cloud (URL pública)
3. Hugging Face Spaces (URL pública)
4. Docker local no hospital

## Resultado da Decisão

**Opção escolhida:** "Streamlit local no PC do hospital", porque é a única opção que atende simultaneamente: zero dependência da TI, dados na rede interna, custo zero, e deploy imediato com stack já disponível (Python + venv).

**Evolução planejada:** na Fase 8 (Industrialização), o app será containerizado com Docker, o que permitirá deploy em qualquer ambiente — incluindo uma versão de portfólio pública. Essa evolução está documentada no roadmap e não justifica antecipar complexidade agora.

### Como funciona

1. Ediney ativa o venv e roda `streamlit run app.py` no PC do hospital
2. Streamlit sobe na porta padrão (8501) e fica acessível na LAN
3. Assistente acessa `http://<IP-DO-PC>:8501` no navegador
4. Autenticação por senha via `st.secrets`
5. Ao final do uso, Ediney encerra o processo

### Confirmação

* Testar acesso da máquina da assistente ao IP:porta do PC do Ediney antes de considerar o deploy concluído
* Documentar IP e procedimento no runbook RB-002

### Consequências

* **Positiva:** Zero dependência de serviços externos ou liberações da TI
* **Positiva:** Dados nunca saem da rede interna do hospital
* **Positiva:** Deploy em minutos — `pip install streamlit` + `streamlit run`
* **Positiva:** Proporcional ao problema (1 usuária, uso mensal)
* **Negativa:** Disponibilidade amarrada ao PC do Ediney estar ligado e ao app rodando (aceitável dado o padrão de uso)
* **Negativa:** Não é production-grade — servidor de desenvolvimento do Streamlit. Aceitável para o volume atual; será substituído por container na Fase 8

## Prós e Contras das Opções

### Streamlit local (rede interna)

* ✅ Atende todas as restrições hospitalares sem exceção
* ✅ Custo zero, zero config de infra
* ✅ Dados permanecem na LAN
* ❌ Disponibilidade depende do PC ligado
* ❌ Servidor de desenvolvimento, não production-grade

### Streamlit Community Cloud

* ✅ Deploy automático via GitHub, URL fixa, 24/7
* ✅ Bom para portfólio (URL pública)
* ❌ Domínio provavelmente bloqueado pelo firewall hospitalar
* ❌ Dados transitam pela internet pública
* ❌ Cold start após inatividade (5-10s)

### Hugging Face Spaces

* ✅ Comunidade ML forte, alternativa ao Streamlit Cloud
* ❌ Mesmos problemas de firewall e dados na internet
* ❌ Menos integração nativa com Streamlit

### Docker local no hospital

* ✅ Containerização é prática sênior (valor de portfólio)
* ✅ Mais robusto e reprodutível
* ❌ TI provavelmente não libera instalação do Docker
* ❌ Overhead desproporcional para 1 usuária e 900 linhas/mês
* ❌ Planejado para Fase 8 — antecipar é premature optimization

## Mais Informações

* Roadmap Fase 8: containerização com Docker como evolução natural desta decisão
* Runbook RB-002 (a criar): procedimento operacional para a assistente usar a GUI
* Documentação Streamlit sobre deploy em rede local: https://docs.streamlit.io/