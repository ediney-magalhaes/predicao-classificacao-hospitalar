# Histórico de Alterações (Changelog) - Projeto Classificação SUS

Este documento registra as principais mudanças no script de classificação.

---
## v3.0 (Novembro de 2025)
* **Assunto:** Otimização de Performance e Combate ao "Data Drift".
* **Mudança:** O script principal (`script_classificacao_sus_otimizado_v3.py`) foi modificado para filtrar o histórico de treinamento.
* **Motivo:** A análise de distribuição temporal (feita em Outubro) provou que o perfil do `grupo_sus` mudou significativamente desde 2012, enquanto a `complexidade_sus` se manteve estável.
* **Ação:** O script agora treina os modelos **apenas com dados de 2020 em diante**.
* **Resultado:** A performance dos modelos aumentou drasticamente (ex: precisão da Alta Complexidade de 73% para 89% e F1-score do Grupo SUS de 0.63 para 0.87).

---
## v2.0 (Setembro de 2025)
* **Assunto:** Implementação do Balanceamento de Classes.
* **Mudança:** Introduzida a biblioteca `imbalanced-learn` e a técnica **SMOTE** no pipeline de treinamento.
* **Motivo:** O modelo original (v1.0) tinha baixo recall (56%) para "Alta Complexidade".
* **Ação:** O pipeline foi refeito para usar `ImbPipeline` e `SMOTE`, e foram adicionadas etapas de limpeza de "classes raras" (com < 10 membros) para estabilizar o treinamento.
* **Resultado:** O recall da "Alta Complexidade" saltou de 56% para 84%, melhorando drasticamente a utilidade do modelo.

---
## v1.0 (Setembro de 2025)
* **Assunto:** Modelo Base e Regra de Negócio.
* **Mudança:** Versão inicial do script.
* **Funcionalidades:**
    1.  Treinamento de dois modelos `LightGBM` (Grupo e Complexidade) com todos os dados históricos (2012+).
    2.  Geração de predições em novos arquivos.
    3.  Implementação de uma "camada de correção" (regra de negócio) na Parte B para forçar a classificação "cirúrgico" em casos onde um código de cirurgia estava presente.