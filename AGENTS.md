# Instruções para agentes de IA (AGENTS.md)

Este arquivo orienta qualquer IA que trabalhe no PrintRoute (Claude Code, Copilot, Codex, Cursor…).
O `CLAUDE.md` só importa este arquivo. **Mantenha-o atualizado** quando o processo, os comandos ou a
estrutura mudarem: ele faz parte da documentação.

## O projeto em uma frase

Impressora virtual para Windows que reencaminha a impressão recebida para uma ou mais impressoras reais
(pré-configuradas, ou escolhidas na hora), compilada em um `.exe`. **Windows-only** (usa APIs do spooler
de impressão do Windows). Licença AGPL-3.0.

## Estado atual: ainda não há funcionalidade real

Este repositório tem a esteira completa de desenvolvimento e só um esqueleto do programa (janela Tkinter
vazia, `src/printroute/__main__.py`). **Não implemente reencaminhamento de impressão sem o dono decidir
a arquitetura antes** (veja abaixo). Não assuma que uma API ou biblioteca específica já foi escolhida.

## Risco técnico em aberto

Uma impressora virtual de verdade no Windows precisa de um **port monitor** registrado no spooler
(`spoolsv.exe`), que tipicamente é uma **DLL nativa** (C/C++). O `pywin32`/`win32print` administra
impressoras, portas e trabalhos de impressão via API, mas **não** cria um port monitor do zero em Python
puro. Produtos parecidos (ex.: RedMon) resolvem isso com um monitor nativo já pronto que encaminha os
bytes brutos para um processo externo — esse processo externo (a lógica de destino, o seletor etc.) pode
ser Python. Essa decisão de arquitetura é a primeira pergunta do primeiro épico do projeto: não a tome
sozinho, discuta com o dono antes de implementar qualquer captura real de impressão.

## `pyproject.toml` é a referência

Consulte **sempre** o `pyproject.toml` antes de assumir qualquer coisa sobre o projeto:

- **Python mínimo** (`requires-python`): não use recursos de versões mais novas que ele.
- **Versão**: o `pyproject.toml` a lê do `src/printroute/version.py`. Nunca escreva a versão em outro
  lugar, e nunca a altere à mão: é a esteira que sobe a versão ao integrar uma release.
- **Estilo e qualidade**: a configuração do Ruff (`[tool.ruff]`). Rode `uvx ruff check .` no que você mexer.
- **Dependências**: hoje o programa não tem dependências de execução (`dependencies = []`) — vai
  precisar de uma quando a arquitetura de captura de impressão for decidida (provavelmente `pywin32`).
  A de build (o PyInstaller) fica **só** no `requirements-build.txt`. Não a duplique no `pyproject.toml`.
- Se precisar de uma configuração nova de ferramenta, ela vai no `pyproject.toml`, e não em arquivos soltos.

## Comandos

| Para… | Rode |
|---|---|
| Rodar o programa | `python src/printroute/__main__.py` (ou `python -m printroute` com `pip install -e .`) |
| Testes (obrigatório antes de todo commit) | `python -m unittest discover -s tests` |
| Lint (roda na CI; tem que ficar sem avisos) | `uvx ruff check .` |
| Compilar para Windows | `python packaging/windows/build_exe.py` (num Windows, com `pip install -r requirements-build.txt`) |
| Instalar para desenvolver | `pip install -e .` |

A saída do compilador vai para `build-local/`, que é ignorada pelo Git. Apague o que você gerou
(`build-local/`, `__pycache__/`) ao terminar: o clone do dono deve ficar limpo.

## Estrutura

| Pasta | Conteúdo |
|---|---|
| `src/printroute/` | O programa (pacote). Mexer aqui **muda o executável** e exige uma versão nova. |
| `tests/` | Testes (`unittest`), inclusive dos scripts da esteira. |
| `packaging/windows/` | Compilador do `.exe`. |
| `scripts/processo/` | Configuração do GitHub (labels, painéis, automações). |
| `.github/` | Workflows e scripts da esteira, modelos de issue e PR. |
| `docs/processo.md` | O processo completo. Leia antes de mexer na esteira. |

## Processo (resumo; completo em `docs/processo.md`)

1. **Tudo nasce de um épico**, refinado com "Muda o programa?", escopo, critérios de aceite e *Tarefas previstas*.
2. **Iniciar sprint** e **Criar branches** são botões (`gh workflow run iniciar-sprint.yml` / `criar-branches.yml`).
   Rode **sempre com `-f simular=true` antes**. Não crie issues, milestones nem branches de tarefa à mão.
3. **Sprint não é versão.** O milestone `vX.Y.Z` existe só para o que muda o programa (`src/` ou
   `requirements-build.txt`). Tudo o mais é `sem-executavel`: roda sem versão e sem milestone.
4. **Uma tarefa = uma branch `feature/<n>-<slug>` = um PR para a `develop`**, com `Refs #<n>` (nunca
   `Closes`: as issues fecham sozinhas na publicação).
5. **Ao começar a programar uma tarefa, mova o cartão para *Code*:**
   `PROJETO_OWNER=BrunodosSantosVaz GITHUB_REPOSITORY=BrunodosSantosVaz/print-route bash .github/scripts/projeto.sh mover <n_do_painel> <n_da_tarefa> "Code"`.
6. **Todo PR tem testes** e a CI verde (`check` e `regras` são obrigatórios).
7. **PR `sem-executavel` não leva a label `aprovado`**: é mesclado direto na `develop` (merge commit, na
   ordem das dependências) e finalizado por *Publicar sem executável*. PR que muda o programa leva
   `aprovado`, e a esteira integra a release e gera a candidata para homologação.

## O que a IA nunca faz sem pedido explícito do dono

- Decidir a arquitetura de captura de impressão (veja [Risco técnico em aberto](#risco-técnico-em-aberto))
  ou implementar qualquer coisa que registre um port monitor, driver ou serviço no Windows.
- Aprovar PR (label `aprovado`), mover cartão para *Aprovado*/*Reprovado*, aprovar o ambiente `producao`
  ou rodar *Publicar em produção* / *Publicar sem executável*. Uma autorização vale **só** para a sprint
  em que foi dada.
- Commitar direto na `main` ou na `develop`, forçar push, reescrever histórico ou apagar tags.
- Mudar o comportamento do programa numa tarefa `sem-executavel`, ou tocar `src/` fora de uma versão.
- Alterar `packaging/windows/build_exe.py` sem necessidade: ele gera o `.exe` oficial e o portão da
  produção o compara com o da candidata.

## Regras de código

- **Sem dados reais de terceiros** em código, testes ou capturas de tela (nomes de impressoras reais,
  caminhos de rede, conteúdo de documentos impressos).
- **Nomes, comentários, commits e documentação em português do Brasil**, como o resto do projeto. Commits
  no formato `tipo: resumo` (`feat`, `fix`, `docs`, `test`, `refactor`, `build`, `chore`).
- Código simples: funções curtas, uma responsabilidade por módulo, sem repetição. Prefira ajustar o que
  já existe a criar outro caminho para a mesma coisa.
- Nada de dependência nova sem necessidade concreta e sem citar por quê no PR (o programa hoje não tem
  nenhuma dependência de execução).
