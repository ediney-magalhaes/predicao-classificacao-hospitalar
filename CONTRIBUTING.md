# Guia de Contribuição (Contributing)

Obrigado por investir seu tempo em contribuir para o **Sistema Preditivo de Classificação SUS**! Este documento estabelece as diretrizes de desenvolvimento, versionamento e boas práticas para garantir a escalabilidade e a governança do código.

---

## 1. Configuração do Ambiente Local

Antes de iniciar qualquer desenvolvimento, garanta que o seu ambiente está espelhado com o de produção:

1. Clone o repositório.
2. Crie e ative um ambiente virtual (VENV):
    ```bash
    python -m venv venv
    source venv/bin/activate  # Linux/Mac
    venv\Scripts\activate     # Windows
    ```

3. Instale as dependências rigorosamente mapeadas:
    ```bash
    pip install -r requirements.txt
    ```

4. Solicite ao administrador o arquivo `.env` contendo o *Salt* criptográfico e os caminhos de credenciais. **Nunca** suba chaves ou dados reais de pacientes para o repositório.

---

## 2. Padrão de Nomenclatura de Branches

A branch `main` é sagrada e reflete o que está em produção. Todo novo desenvolvimento deve ser feito em uma branch derivada, seguindo os prefixos abaixo:

* `feature/`: Para novas funcionalidades, modelos de IA ou scripts (ex: `feature/previsoes_fevereiro`).
* `bugfix/`: Para correções de erros no código ou na modelagem (ex: `bugfix/duplicidade_merge_cirurgia`).
* `hotfix/`: Para correções críticas e urgentes em produção na branch main.
* `docs/`: Para criação ou atualização de documentação.

**Comando de exemplo:**
    ```bash
    git checkout -b feature/nome_da_sua_branch
    ```

---

## 3. Padrão de Commits (Conventional Commits)

Nós utilizamos a convenção semântica para mensagens de *commit*. Isso facilita a leitura do histórico e a geração automática de *Changelogs*. A estrutura deve ser:

`tipo(escopo opcional): descrição clara e no imperativo`

**Tipos permitidos:**
* `feat:` Uma nova funcionalidade ou nova feature de Machine Learning.
* `fix:` Correção de um bug.
* `docs:` Mudanças apenas na documentação (README, Changelog, etc.).
* `refactor:` Uma mudança de código que não corrige um bug nem adiciona uma feature.
* `perf:` Uma mudança de código que melhora a performance.
* `chore:` Atualizações de tarefas de build, configurações de pacotes, etc.

**Exemplos Práticos:**
* ❌ `git commit -m "arrumei o erro das cirurgias multiplicando"`
* ✅ `git commit -m "fix: resolve duplicidade no merge de cirurgias no script de previsao"`
* ✅ `git commit -m "feat(ml): injeta colunas semanticas do CID-10 no pipeline de treino"`

---

## 4. Fluxo de Pull Requests (PR)

1. Faça o push da sua branch para o GitHub.
2. Abra um **Pull Request (PR)** apontando para a `main`.
3. No corpo do PR, descreva claramente o problema que está sendo resolvido e o impacto nos dados.
4. O PR só será aprovado após Code Review de um líder técnico do projeto e após a confirmação de que a acurácia dos modelos não foi degradada.