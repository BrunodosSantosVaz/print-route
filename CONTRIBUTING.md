# Contribuindo com o PrintRoute

Obrigado por querer ajudar! Este guia mostra como contribuir sem tropeços. O processo completo
(painéis, branches, releases) está em [docs/processo.md](docs/processo.md).

## O projeto está no início

Ainda não há funcionalidade real de reencaminhamento de impressão, e a arquitetura (como interceptar a
impressão no Windows) ainda não foi decidida — veja [AGENTS.md](AGENTS.md#risco-técnico-em-aberto). Antes
de programar algo grande, **discuta primeiro** em [Discussions](https://github.com/BrunodosSantosVaz/print-route/discussions)
ou numa issue: evita trabalho jogado fora numa direção que ainda pode mudar.

## Jeitos de contribuir

- **Dúvida, ideia ou discussão de arquitetura?** Use o [Discussions](https://github.com/BrunodosSantosVaz/print-route/discussions)
  (Q&A e Ideas). Assim as Issues ficam só com trabalho concreto. Uma ideia que amadurece vira épico pelas
  mãos do mantenedor: você **não** precisa abrir o formulário de Épico.
- **Achou um bug?** Abra uma issue com o formulário **Bug** (versão, passos para reproduzir, resultado
  esperado × obtido).
- **Achou uma vulnerabilidade?** Não abra issue: use o relato privado ([SECURITY.md](SECURITY.md)).
- **Quer programar?** Comente numa issue existente (ou abra uma) antes de começar, para alinharmos o
  escopo. Issues com a label `good first issue` são um bom começo. **Toda alteração precisa de issue**,
  inclusive uma correção pequena de documentação, porque o número dela vai no nome da branch.

## Ambiente de desenvolvimento

Os metadados do projeto, a versão mínima do Python e a configuração do Ruff ficam no `pyproject.toml`. Se
você usa uma IA para programar, ela segue o [`AGENTS.md`](AGENTS.md) (o Claude Code o lê pelo `CLAUDE.md`).

Requer **Python 3.10 ou superior com Tkinter** (o instalador oficial do Python para Windows já inclui).
O programa não usa bibliotecas externas.

```powershell
git clone https://github.com/BrunodosSantosVaz/print-route.git
cd print-route
python src\printroute\__main__.py                  # rodar (ou python -m printroute com pip install -e .)
python -m unittest discover -s tests -v            # testes
uvx ruff check .                                   # estilo (regras no pyproject.toml; roda na CI)
pip install -r requirements-build.txt              # só para gerar o .exe
python packaging\windows\build_exe.py              # gera em build-local/ (ignorada pelo Git)
```

## Fluxo de trabalho

1. Faça um **fork** e clone-o. A base do trabalho é a branch **`develop`** (não a `main`).
2. Crie a branch a partir da `develop` com o **número da issue**:
   `feature/<n>-<slug>` (tarefa) ou `bugfix/<n>-<slug>` (bug). Ex.: `feature/12-selecionar-impressora`.
3. Faça mudanças **pequenas e focadas** (um assunto por pull request) e **inclua testes**.
4. Abra o PR **para a `develop`** com `Refs #<n>` na descrição, preenchendo o modelo. O CI (`check`) e o
   `Regras do PR` precisam passar. O primeiro PR de quem é novo no projeto pode esperar a aprovação do
   mantenedor para o CI rodar.
5. Responda à revisão com novos commits na mesma branch.

### O que acontece depois

Só o mantenedor mescla, aprova e publica. Você não mexe em versão, `CHANGELOG.md` nem em release. Quando o PR
é aprovado (label `aprovado`) e todos os PRs da sprint estão aprovados, a esteira monta a release, gera a
candidata `vX.Y.Z-rc.N` e a leva para homologação; testada e aprovada, é publicada e a sua issue é fechada
sozinha. Os seus commits mantêm a sua autoria. Não há prazo garantido (projeto mantido em tempo parcial).
Um PR que muda o programa só entra em uma release se a issue dele estiver no milestone de uma versão: o
mantenedor decide isso.
Se o PR só mexe em documentação, testes, automação ou o compilador (nada em `src/` nem em
`requirements-build.txt`), ele recebe sozinho a label `sem-executavel`: não entra em versão, não passa por
homologação nem pela label `aprovado`, é mesclado pelo mantenedor direto na `develop` e chega à `main` quando
ele roda o botão *Publicar sem executável*. Só gera versão (e executável) o que muda o programa; a sprint,
que é o período de trabalho, pode não ter versão nenhuma (veja
[docs/processo.md](docs/processo.md#sprint-não-é-versão)).

Mensagens de commit: uma linha objetiva, de preferência no formato `tipo: resumo`
(`feat`, `fix`, `docs`, `test`, `chore`, `refactor`).

## Padrões do código

- **Só biblioteca padrão** por enquanto (`pywin32` ou outra dependência de execução só entram com
  discussão prévia, quando a arquitetura de interceptação de impressão for decidida).
- **Sem dados reais de terceiros** em código, testes ou capturas de tela (nomes de impressoras, caminhos
  de rede, documentos impressos).
- **Textos** em português do Brasil, com acentuação correta.

## Testes

`python -m unittest discover -s tests -v` precisa passar. Para um bug, escreva primeiro o teste que
falha (regressão) e depois a correção.

## Licença

Ao contribuir, você concorda que sua contribuição seja distribuída sob a [Licença AGPL-3.0](LICENSE) do
projeto. Veja também o [Código de Conduta](CODE_OF_CONDUCT.md).
