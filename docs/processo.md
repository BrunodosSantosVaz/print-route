# Processo de desenvolvimento e entrega

Como o PrintRoute é planejado, desenvolvido, testado e publicado. Vale para quem mantém o projeto e
para quem quer contribuir. O PrintRoute é um **aplicativo compilado** (um `.exe` para Windows), então
não existe "deploy em servidor": **publicar uma versão** ocupa o lugar do deploy, e **a versão diz o
ambiente**.

A esteira é **automática de ponta a ponta**. Os únicos gestos humanos são: escolher os épicos da
sprint, revisar e aprovar cada PR, testar a candidata e aprovar (ou reprovar) cada cartão, e apertar
*Publicar em produção*.

## Princípios

1. **Nada começa sem decisão.** Toda mudança nasce em um **épico** discutido até uma conclusão.
2. **Toda tarefa inclui os seus testes automatizados.** Sem teste, a tarefa não está pronta.
3. **Mudanças pequenas e frequentes**: um pull request por tarefa.
4. **O Git guarda o código; a GitHub Release guarda o executável.** Binários não entram no repositório: cada versão pode ser recompilada a partir da sua tag.
5. **Toda homologação tem versão.** Sempre existe uma release candidata (`rc`) antes de testar.
6. **O binário aprovado é o publicado.** A produção não recompila: promove o mesmo arquivo da candidata.
7. **O build é automático; o "ok" humano é explícito** (label `aprovado` no PR, cartão *Aprovado*, botão de produção).
8. **Todo bug vira issue, ganha um teste de regressão e uma versão de correção.**
9. **O processo é cobrado por ferramenta** (rulesets, CI, portões dos scripts, aprovação de ambiente), não só por combinado.
10. **Cada etapa é testada** antes de avançar: CI no PR, testes na release, candidata em homologação, portão na produção.

## A esteira em uma tela

```
Épico (Planejamento)                     Tarefa (Execução)                          Versão
────────────────────                     ─────────────────                          ──────
Brainstorm … Próxima sprint
      │  ① Iniciar sprint  ─────────►  A fazer
Em desenvolvimento                          │  ② Criar branches
      │                                  Feature ── feature/<n>-<slug>
      │                                     │  commits + push          (automático)
      │                                    Code
      │                                     │  abrir PR → develop      (automático)
      │                                  CI/PR ── CI verde + revisão ── label "aprovado" no PR
      │                                     │  ③ Integrar release      (automático, quando TODOS aprovados)
      │                                     │     release/x.y.z: merge um a um, versão, CHANGELOG
      │                                     │     ④ Release candidata vX.Y.Z-rc.N  (automático)
      │                                  Homologação ── você testa o .exe da rc
      │                                     ├── Reprovado ─► ② de novo ─► Code ─► … ─► rc.N+1
      │                                  Aprovado
      │  ⑤ Publicar em produção  ◄──────────┘  (todos Aprovados)
Concluída                                Concluído                      vX.Y.Z (Latest): .exe
```

Os passos numerados são os únicos **botões** (Actions → *Run workflow*, ou `gh workflow run`). Tudo o
mais roda sozinho, movendo os cartões conforme o que acontece no GitHub.

> **Atalho para o que não mexe no programa.** Documentação, testes, workflows e scripts não entram no
> executável. Essas issues levam a label `sem-executavel`: **pulam a homologação e a release** e são concluídas
> pelo botão *Publicar sem executável*. Veja [Alterações que não afetam o executável](#alterações-que-não-afetam-o-executável).

## Ambientes: a versão diz onde está o executável

O executável fica sempre no mesmo lugar, a página de
[Releases](https://github.com/BrunodosSantosVaz/print-route/releases), e o **estado da versão** indica o ambiente:

| Ambiente | Como reconhecer | Exemplo |
|----------|-----------------|---------|
| **Produção** | release marcada **Latest**, versão `X.Y.Z` | `v0.2.0` |
| **Homologação** | **Pre-release** com versão `X.Y.Z-rc.N` (a `N` sobe a cada correção) | `v0.3.0-rc.2` |
| Build de tarefa (opcional) | artefato temporário do CI na `develop` (14 dias), sem versão | `PrintRoute-tarefa-<sha>` |

Enquanto não houver candidata aberta, **a homologação é a própria versão em produção**. Ao integrar uma
nova versão, a candidata `rc.1` passa a ser a homologação; quando ela é aprovada e publicada, produção e
homologação voltam a ser a mesma versão.

O nome do arquivo carrega o estágio (`PrintRoute-v0.3.0-rc.2-windows-x64.exe` ou
`PrintRoute-v0.3.0-windows-x64.exe`), mas o **conteúdo do binário é o mesmo** da candidata para a
produção (o `rc` só existe no nome, e o SHA-256 é idêntico). O executável fica **só nas Releases**, não
no repositório.

O compilador fica em `packaging/windows/build_exe.py` (PyInstaller, rodando no Windows do CI).

## Sprint não é versão

Segue o padrão do mercado: **sprint** é um período de trabalho; **versão** é o que é entregue.

| | O que é | Onde fica |
|---|---|---|
| **Sprint** | período de trabalho (2 semanas), com ou sem versão | campo **Sprint** (*Iteration*) dos painéis Planejamento e Execução |
| **Versão** | o programa compilado que muda (`vX.Y.Z`) | **milestone** `vX.Y.Z`, tag e GitHub Release |

- **Só gera versão o que muda o programa** (`src/` ou `requirements-build.txt`). Documentação, testes, esteira e
  o compilador não geram versão nem executável: é a label **`sem-executavel`**.
- **Milestone é só versão real.** Não existe milestone de sprint nem milestone "sem compilar".
- O executável é sempre o da **última versão real**.
- Uma sprint pode ter só épicos `sem-executavel` (**sprint sem versão**: nenhum milestone, nada compilado), só
  épicos que mudam o programa (sprint com versão) ou os dois (**sprint mista**: o milestone vale só para as
  tarefas que mudam o programa).

O épico diz no formulário se **muda o programa**. Com "Não", ele nasce com a label `sem-executavel`, e as tarefas
dele também. A label pode ser posta ou tirada à mão depois; a esteira respeita o estado atual. Épico antigo, sem
essa resposta, é tratado como "muda o programa" (o caminho seguro, que exige versão).

## Painéis (GitHub Projects)

| Painel | Para quê | Colunas |
|--------|----------|---------|
| **PrintRoute — Planejamento** | épicos, do brainstorm à sprint (campo **Sprint**) | Brainstorm → Backlog → Backlog Refinement → Validar protótipo → Próxima sprint → Em desenvolvimento → Concluída |
| **PrintRoute — Execução** | tarefas, da branch à produção (campos **Sprint** e **Milestone**) | A fazer → Feature → Code → CI/PR → Homologação → Aprovado / Reprovado → Concluído |
| **PrintRoute — Bugs** | planejamento e execução juntos | Novo → Em correção → CI/PR → Homologação → Aprovado / Reprovado → Corrigido |

| Coluna | Significa | Quem move |
|--------|-----------|-----------|
| **A fazer** | tarefa criada (na sprint ou no backlog) | automático (issue criada) |
| **Feature** | a branch `feature/<n>-<slug>` existe | *Criar branches* / push da branch |
| **Code** | há commits na branch | push |
| **CI/PR** | PR aberto para a `develop` (CI e revisão) | PR aberto |
| **Homologação** | mesclada na `develop` e/ou dentro da release candidata: **hora de testar o `.exe`** | merge do PR, *Integrar release* (issues `sem-executavel` pulam esta coluna) |
| **Aprovado** | você testou a candidata e a tarefa está ok | **você** (arrastar o cartão); `sem-executavel`: **automático** ao mesclar o PR |
| **Reprovado** | você testou e não está ok | **você** (arrastar o cartão) |
| **Concluído / Corrigido** | publicado em produção | *Publicar em produção* (ou *Publicar sem executável*) |

Não confunda os dois "aprovados": a **label `aprovado` no PR** significa "revisei o código, pode entrar na
release" (dispara a integração); o **cartão *Aprovado*** significa "testei o `.exe` da candidata, pode ir
para produção" (libera o portão da produção).

## Tipos de issue e labels

| Tipo | Label | Painel |
|------|-------|--------|
| Épico | `epic` | Planejamento |
| Tarefa (sub-issue de um épico) | `task` | Execução |
| Bug | `bug` | Bugs |

**Dúvidas, ideias soltas e conversa não são issues:** vão para o Discussions e não viram cartão. Uma ideia que amadurece
vira **épico** (converter a discussão em issue). A publicação de cada versão é anunciada automaticamente na
categoria *Anúncios*.

Outras labels: `aprovado` (PR revisado), `sem-executavel` (não altera o executável), `hotfix`, `testing`, `documentation`, `enhancement`, `dependencies`,
`prioridade:*`, `severidade:*`, `good first issue`, `help wanted`.

## Branches

| Branch | Papel | Recebe | Vai para |
|--------|-------|--------|----------|
| `main` | o que foi **publicado** | só `release/*` e `hotfix/*` | Release (produção) |
| `develop` | integração | `feature/*`, `bugfix/*` | build de tarefa (CI) |
| `feature/<n>-<slug>` | uma tarefa (n = nº da issue) | nasce da `develop` (criada pela esteira) | PR para a `develop`; apagada ao encerrar |
| `bugfix/<n>-<slug>` | bug achado antes de publicar | nasce da `develop` | PR para a `develop`; apagada ao encerrar |
| `release/x.y.z` | reúne a versão e gera as candidatas | nasce da `develop` (criada pela esteira) | PR para a `main`; **apagada ao encerrar** (a versão fica na tag `vX.Y.Z`) |
| `hotfix/<n>-<slug>` | bug urgente na versão publicada | nasce da `main` | PR para a `main`; apagada ao encerrar |

No repositório, **em repouso, só existem `main` e `develop`**. As demais branches são temporárias, como no
GitFlow: `feature/*`, `bugfix/*`, `hotfix/*` e `release/*` são apagadas quando a versão (ou a sprint sem
versão) é encerrada. **Quem guarda cada versão é a tag** `vX.Y.Z` (imutável, aponta para o commit publicado)
e a GitHub Release; as tags nunca são apagadas. Manter uma branch de release só seria necessário com várias
versões recebendo correção em paralelo (ex.: `release/1.x`), o que não é o caso.

### Como a `release/x.y.z` é apagada (travas de segurança)

No fim do encerramento (*Publicar em produção*, *Pós-publicação* ou o botão *Encerrar sprint*), o
`encerrar-sprint.sh` chama o `.github/scripts/apagar-release.sh`. Ele só apaga se **todas** as travas passam;
se uma falha, a branch **fica** e sai um aviso com o motivo (a publicação não é derrubada):

1. nome exato `release/<x.y.z>` (semver): nada de curingas;
2. a **tag** de produção `vX.Y.Z` existe (a da candidata `-rc.N` não conta);
3. a **GitHub Release** `vX.Y.Z` existe (a versão foi publicada);
4. a branch está **contida na tag** (`compare vX.Y.Z...release/x.y.z` com `ahead_by == 0`): nenhum commit fica de fora;
5. a branch está **contida na `main`** (`ahead_by == 0`): foi mesclada.

**Tags nunca são apagadas nem movidas**: a única escrita é `DELETE git/refs/heads/release/<x.y.z>`. Para limpar
uma branch antiga à mão, rode primeiro a simulação:

```bash
VERSAO=v0.2.0 SIMULAR=true  GITHUB_REPOSITORY=BrunodosSantosVaz/print-route bash .github/scripts/apagar-release.sh
VERSAO=v0.2.0 SIMULAR=false GITHUB_REPOSITORY=BrunodosSantosVaz/print-route bash .github/scripts/apagar-release.sh
```

### Voltar a uma versão antiga (rollback)

Tudo continua possível **pela tag**, com ou sem a branch de release:

| Quero… | Como |
|---|---|
| **Usar** a versão antiga | Baixar o executável da [Release](https://github.com/BrunodosSantosVaz/print-route/releases) da versão. Para um app compilado, esse é o rollback: não há servidor para voltar. |
| **Ver o código** como estava | `git switch --detach v0.1.0`, ou no GitHub em *Code → Tags → v0.1.0*. `git show v0.1.0:src/printroute/version.py` mostra `0.1.0`. |
| **Recompilar** a versão antiga | `git switch --detach v0.1.0` e rode `python packaging/windows/build_exe.py` (o compilador que vem na própria tag). |
| **Corrigir** a versão antiga (hotfix) | `git switch -c hotfix/<n>-<slug> v0.1.0`: a tag é o ponto de partida, e o fluxo de hotfix segue igual. |
| **Voltar a `main`** para o código antigo | `git revert` dos commits posteriores (ou uma versão nova que desfaz a mudança), por PR, como qualquer alteração. |

Regras: nunca commitar direto na `main` ou na `develop`; PR com `Refs #n` (não `Closes`: as issues
fecham na publicação); as atualizações do Dependabot (`dependabot/**`, agrupadas em um PR por mês) vão para a `develop` e
não exigem issue; o workflow **Regras do PR** confere nome de branch, destino e referência à issue, e avisa
se o PR não mexe em testes.

## Quem contribui de fora

O projeto é open source: quem não é o mantenedor participa por três caminhos, todos descritos para o
público no [README](../README.md#contribuindo) e no [CONTRIBUTING](../CONTRIBUTING.md).

| Caminho | Onde | O que a esteira faz |
|---------|------|---------------------|
| **Sugestão ou dúvida** | Discussions (*Q&A*, *Ideas*) | Nada: não vira issue nem cartão. Uma ideia madura é convertida pelo mantenedor em **épico** |
| **Bug** | Issue, formulário *Bug* | A label `bug` vem do formulário e o cartão nasce em *Novo* (painel Bugs) |
| **Alteração no código** | Fork + pull request para a `develop` | Entra na esteira normal, a partir do passo 4 do ciclo. Se só mexe em docs/testes/CI, recebe `sem-executavel` (sem homologação nem versão) |
| **Vulnerabilidade** | Relato privado (*Security advisories*) | Fora da esteira; nunca em issue pública |

Os formulários *Épico* e *Tarefa* existem para o planejamento do mantenedor; quem vem de fora não precisa deles.

### Regras do pull request de fora

1. **Toda alteração tem uma issue**, inclusive correção pequena de documentação: o número dela está no
   nome da branch. Não há atalho para PR só de texto.
2. Branch `feature/<n>-<slug>` ou `bugfix/<n>-<slug>`, criada a partir da `develop`, e PR para a `develop`
   com `Refs #<n>`. A **Regras do PR** reprova o que sair desse padrão.
3. Testes junto com a mudança (a falta de teste só avisa; a revisão cobra). Só biblioteca padrão, sem
   dados reais de terceiros em código, testes ou capturas de tela.
4. Checks obrigatórios para mesclar: `check` e `regras` (mais compatibilidade, scripts Linux e CodeQL).

### O que acontece com o PR

| Passo | Quem | O que |
|-------|------|-------|
| CI e regras | automático | Rodam no PR. Em PR de fork o workflow **não recebe os segredos** (`PROJETO_TOKEN`) |
| Revisão | mantenedor | Comenta, pede ajustes, coloca a label `aprovado` (só quem tem escrita consegue) |
| Integração | mantenedor | Para PR de fork use o botão *Integrar release*: a label não dispara a integração automática de forks. O script busca o PR em `refs/pull/N/head` e os commits entram com `--no-ff`, preservando a autoria |
| Candidata e produção | esteira | Igual às tarefas internas: `rc.N`, homologação, *Publicar em produção*; a issue fecha sozinha |

Quem contribui **não pode** mesclar, aprovar, pôr labels, mover cartões, rodar os botões, aprovar o
ambiente `producao` nem empurrar direto na `main`/`develop`. O PR só entra em uma release se a issue dele
estiver no **milestone de uma versão**; sem milestone, a integração responde "nada a integrar" e o
mantenedor decide entre encaixá-la em uma versão ou mesclar na `develop` à mão. PR `sem-executavel` nunca entra
em versão: é mesclado direto na `develop`.

## Ciclo de uma sprint, passo a passo

### 1. Épico → sprint (humano)
Ideia em *Brainstorm*, refinada até ter escopo, critérios de aceite, plano de testes e a lista **Tarefas
previstas** (uma por linha, cada uma cabendo em um PR pequeno). O formulário pergunta se o épico **muda o
programa** (com "Não", ele recebe a label `sem-executavel`). O dono arrasta os épicos escolhidos para
*Próxima sprint*.

### 2. Iniciar sprint (botão)
`Iniciar sprint` pega **todos** os épicos de *Próxima sprint*, move-os para *Em desenvolvimento*, põe épicos e
tarefas na **Sprint** (a atual, ou a do campo `sprint`) e cria, para cada épico, as tarefas da lista *Tarefas
previstas* (sub-issues `task`, cartão em *A fazer*). Épico sem a lista fica onde está, com um aviso. Rodar de
novo não duplica nada.

A **versão** (`versao=vX.Y.Z`) só é usada pelos épicos que mudam o programa:

| Épicos na *Próxima sprint* | `versao` | Resultado |
|---|---|---|
| Só `sem-executavel` | vazia | **sprint sem versão**: nenhum milestone; tarefas com a label `sem-executavel` |
| Só `sem-executavel` | informada | a versão é ignorada, com aviso; nenhum milestone |
| Algum que muda o programa | vazia | **recusa** sem criar nada (diz quais épicos precisam de versão) |
| Misto | informada | milestone `vX.Y.Z` (criado se não existe) só nas tarefas dos épicos que mudam o programa |

### 3. Criar branches (botão)
`Criar branches das tarefas` cria `feature/<n>-<slug>` (ou `bugfix/…`) a partir da `develop` para cada
cartão de tarefa em *A fazer* (bug em *Novo*) **que já está em um milestone** (ou, se `sem-executavel`, **numa
Sprint**) e move o cartão para *Feature*. Cartões *Reprovado* também entram: a branch é recriada e o cartão
volta para *Code*. Tarefa de backlog (sem milestone e, se `sem-executavel`, sem Sprint) é ignorada. Os campos
`versao` e `sprint` limitam a uma versão ou a uma Sprint.

### 4. Desenvolver e abrir o PR (dev ou IA, automático nos cartões)
Commits na branch (com testes), push (cartão → *Code*), PR para a `develop` com `Refs #n` (cartão →
*CI/PR*). O CI (`check`, compatibilidade, scripts Linux, CodeQL) e **Regras do PR** rodam. Cada merge
gera um build temporário de tarefa, para testar a mudança isolada. Cartão → *Homologação* quando o PR
é mesclado na `develop`.

### 5. Aprovar o PR (humano) → integração (automático)
Revisado o código, o dono põe a label **`aprovado`** no PR. A cada label, o workflow *Integrar release*
confere o milestone: **se todos os PRs da sprint estão aprovados e com CI verde**, ele:

1. cria (ou reaproveita) `release/x.y.z` a partir da `develop`;
2. mescla as features **uma por uma** (`--no-ff`; PR de fork entra por `refs/pull/N/head`);
3. atualiza o arquivo de versão (`src/printroute/version.py`, achado pelo `versao.sh`) e a seção `## [x.y.z]` do `CHANGELOG.md`;
4. envia a branch.

É **tudo ou nada**: se falta aprovar algum PR, só avisa e espera; se um merge dá conflito, nada é enviado, o
PR conflitante volta para *Code* sem a label e ganha um comentário. Também há o botão manual
(`Integrar release`, com `simular`).

### 6. Release candidata e homologação (automático)
O push em `release/x.y.z` roda *Build release candidata*: testes e compilação do `.exe` no Windows (com
atestado de procedência) e a **pre-release `vX.Y.Z-rc.N`** com o `.exe` e o `SHA256SUMS.txt`. Em seguida:
`release/x.y.z` é levada para a `develop`, os cartões do milestone vão para *Homologação* e é aberto o PR
`release/x.y.z` → `main`.

### 7. Testar e decidir (humano)
O dono testa **o `.exe` da candidata** e arrasta cada cartão para **Aprovado** ou **Reprovado**.

- **Reprovado**: rode `Criar branches` (recria a branch e devolve o cartão para *Code*), corrija, abra o PR
  para a `develop` e ponha `aprovado`. A esteira integra na mesma `release/x.y.z`, gera a `rc.N+1` e volta
  o cartão para *Homologação*. Os cartões já *Aprovado* continuam assim; a `rc.N+1` é o binário que vai para produção, então teste-a antes de publicar.

### 8. Publicar em produção (botão)
Com **todos** os cartões em *Aprovado*, rode `Publicar em produção` (`versao=vX.Y.Z`). A ação tem duas etapas:

- **conferir** (sempre, não altera nada): o **portão** recusa a publicação se houver cartão fora de
  *Aprovado* (os *Reprovado* são listados à parte), se não existir o PR da release ou ele tiver conflito ou
  checks falhando/pendentes, se não existir a candidata da versão, se o código mudou depois dela ou se o
  `CHANGELOG.md` não tiver a seção da versão. Com `simular=true` (padrão), para aqui e mostra o plano.
- **publicar** (`simular=false`, depois da **aprovação do dono** no ambiente `producao`): mescla o PR na `main`,
  **promove o mesmo binário** da candidata (com o hash conferido) a `vX.Y.Z` (Latest, sem recompilar),
  anuncia no Discussions, **finaliza tudo** — fecha as issues, cartões → *Concluído*/*Corrigido*, épicos com
  todas as tarefas prontas → *Concluída*, fecha o milestone, apaga as branches das tarefas e a `release/x.y.z` (com as
  [travas](#como-a-releasexyz-é-apagada-travas-de-segurança); a versão fica na tag) — e devolve a `main` para a `develop`.

Se algo falhar no meio, rode de novo: a ação é idempotente (se a Release já existe, só refaz a limpeza).

### 9. Hotfix
`hotfix/<n>-<slug>` a partir da `main`, com teste de regressão e versão de correção (`x.y.z+1` em
`src/printroute/version.py` e no `CHANGELOG.md`). O push gera a candidata, e o PR para a `main` mesclado por um
humano dispara *Publicar release* (aprovação do ambiente `producao`) e *Pós-publicação* (fecha o bug,
cartão *Corrigido*, back-merge). Esse é o **caminho manual**, que também cobre uma release mesclada na mão.

## Alterações que não afetam o executável

Documentação, testes, workflows, scripts e exemplos **não entram no executável**. Passar por homologação e gerar
uma versão nova só para publicar um texto regravaria o mesmo programa com outro número. Para esse caso existe a
label **`sem-executavel`**.

**O critério é objetivo:** uma mudança altera o executável se toca `src/` (código do programa) ou
`requirements-build.txt` (o que é empacotado). Qualquer outra coisa é `sem-executavel`. (O compilador
`packaging/windows/build_exe.py` não conta; o `conferir-release` continua tratando-o como parte do binário
nas releases normais.)

### Como a label é aplicada

- **No planejamento**: o épico criado com "Muda o programa? Não" recebe a label, e o *Iniciar sprint* a repassa
  para as tarefas dele (sem milestone).
- **Automática**: a **Regras do PR** olha o diff. PR que não toca `src/` nem `requirements-build.txt` recebe a label
  no PR **e na issue** ligada; se depois passar a tocar, a label é retirada dos dois.
- **À mão**: você pode pôr ou tirar a label numa issue (ex.: uma issue antiga).

### O que muda para a issue `sem-executavel`

| Etapa | Issue normal | Issue `sem-executavel` |
|-------|--------------|------------------------|
| PR mesclado na `develop` | cartão → *Homologação* | cartão → **Aprovado** (não há `.exe` para testar) |
| Candidata `rc.N` | cartão → *Homologação* | cartão → **Aprovado** |
| Notas da release (`CHANGELOG.md`) | entra na lista | **fora** (não muda o programa) |
| Finalização | *Publicar em produção* | *Publicar sem executável* (ou junto com a release) |

O PR `sem-executavel` **não leva a label `aprovado`**: você revisa e mescla direto na `develop`, sem esperar a
integração da release. A `develop` exige PR e os checks `check` e `regras` verdes, sem aprovação de revisão.
Mesmo que alguém ponha `aprovado`, o *Integrar release* reconhece o PR `sem-executavel` e não cria versão.

**Como mesclar vários PRs da mesma sprint:** use *Create a merge commit* (não *Squash*), na ordem das
dependências. Se um PR ficou desatualizado depois do merge anterior, use *Update branch* e espere a CI.

**Sprint sem versão, do início ao fim:**
1. Épicos com "Muda o programa? Não" em *Próxima sprint*.
2. `Iniciar sprint` **sem** `versao` → tarefas em *A fazer*, na Sprint, sem milestone.
3. `Criar branches` → `feature/<n>-<slug>`, cartões em *Feature*.
4. Commits e PRs para a `develop` (cartões em *Code* e *CI/PR*); você mescla, e os cartões vão para *Aprovado*.
5. `Publicar sem executável` → a `main` avança, as issues fecham e o épico conclui. Sem versão, candidata ou Release.

### Publicar sem executável (botão)

`gh workflow run publicar-sem-executavel.yml -f simular=false`, com `simular=true` por padrão. Duas etapas: **conferir**
(sempre, não altera nada) e **publicar** (só com `simular=false`, depois da sua aprovação no ambiente `producao`).

O **portão** recusa, sem alterar nada, se:

1. `src/` ou `requirements-build.txt` **diferem entre `main` e `develop`**: há mudança de programa não publicada, e ela exige
   release com homologação;
2. a `main` tem commits que a `develop` não tem (divergiram, ex.: hotfix não devolvido);
3. o check `check` da ponta da `develop` não está verde.

Passado o portão:

1. **avança a `main` até a `develop`** (fast-forward: sem commit de merge, sem versão, sem candidata, sem Release);
2. para cada issue **aberta** com a label e o cartão em **Aprovado**: fecha, cartão → *Concluído* (bug: *Corrigido*),
   conclui o épico se era a última tarefa e apaga a branch da tarefa já mesclada;
3. issues com a label que ainda não estão em *Aprovado* seguem abertas; as **Reprovado** geram um aviso e não são finalizadas.

### Qual botão usar

| Situação | Botão |
|----------|-------|
| Só docs, testes, CI ou scripts na `develop` | **Publicar sem executável** |
| Mudou o programa (`src/` ou dependências) | Integrar release → candidata → **Publicar em produção** |
| Os dois misturados | Release normal. As issues `sem-executavel` vão junto e são fechadas pela própria publicação |

## Conclusão automática dos épicos

Quando a **última tarefa** de um épico é fechada (em produção), o épico é fechado e vai para *Concluída*
no Planejamento. Se o épico ainda tem tarefas abertas, segue em *Em desenvolvimento* (o log mostra
"n/m tarefas concluídas").

## O que cada workflow faz

| Workflow | Disparo | Faz |
|----------|---------|-----|
| `CI` | PR e push | compila, roda os testes (Windows, compatibilidade e scripts Linux) e o lint (Ruff) |
| `CodeQL` | PR, push, semanal | análise estática |
| `Regras do PR` | PR | nome de branch, destino, `Refs #n`, aviso de falta de teste |
| `Kanban automático` | issue, push, PR | move os cartões; conclui tarefa e épico quando a issue fecha |
| `Iniciar sprint` | **botão** | épicos → *Em desenvolvimento*, Sprint, cria tarefas; milestone só para épicos que mudam o programa |
| `Criar branches das tarefas` | **botão** | `feature/*`/`bugfix/*` a partir da `develop` (tarefas com milestone ou `sem-executavel` na Sprint) |
| `Integrar release` | label `aprovado` no PR ou **botão** | `release/x.y.z`, merges, versão e CHANGELOG (ignora PRs `sem-executavel`) |
| `Build release candidata` | push em `release/**`, `hotfix/**` | testes, `.exe`, pre-release `rc.N`; depois homologação |
| `Publicar em produção` | **botão** | portão, merge na `main`, promove, anúncio, finaliza, back-merge |
| `Publicar sem executável` | **botão** | portão (nada de programa mudou), avança a `main` até a `develop`, fecha as issues `sem-executavel` em *Aprovado* |
| `Publicar release` | push na `main` (arquivo de versão) | caminho manual (hotfix): promove a candidata, anúncio |
| `Pós-publicação da release` | após `Publicar release` | caminho manual: encerra issues e devolve a `main` |
| `Encerrar sprint` | **botão** | refaz/completa a limpeza pós-produção de uma versão |
| `Build de tarefa` | merge na `develop` | artefato temporário para testar a tarefa |

Os botões rodam pela aba **Actions** ou por
`gh workflow run <arquivo>.yml -f versao=v0.2.0 -f simular=false` (sprint sem versão: sem o `-f versao`).
**Rode antes com `simular=true`**
(padrão): o script só mostra o que faria.

## Testes automáticos em cada etapa

| Etapa | O que confere |
|-------|---------------|
| PR | `check`: compilação, testes; compatibilidade de Python; scripts em Linux; CodeQL; regras do PR; lint (Ruff) |
| Integração | todos os PRs aprovados e com CI verde; merges sem conflito; versão e CHANGELOG coerentes |
| Candidata | testes de novo na branch da release, build, atestado e SHA-256 |
| Homologação | o teste humano do `.exe` (cartão *Aprovado*/*Reprovado*) |
| Produção | portão: cartões, PR limpo, candidata testada, código e compilador idênticos aos da candidata, hash do binário conferido ao promover |

Os scripts da esteira têm testes próprios (`tests/test_*.py`), rodados pelo job **scripts (Linux)** do CI.

## Como o processo genérico foi adaptado a um app compilado

| Etapa genérica | No PrintRoute |
|----------------|-------------|
| CI (validação do PR) | `CI`: compila, roda os testes (`check` é o gate obrigatório) |
| Homologação | **release candidata versionada** (`vX.Y.Z-rc.N`, pre-release), criada antes de testar |
| Produção | `Publicar em produção`: promove a candidata aprovada a `vX.Y.Z` (ambiente `producao` com aprovação) |
| Migrações, backup, rollback | não se aplicam; o "rollback" é o usuário voltar a uma release anterior (veja [Voltar a uma versão antiga](#voltar-a-uma-versão-antiga-rollback)) |
| Pós-deploy | dentro da própria ação: issues, cartões, épicos, milestone, branches e back-merge `main` → `develop` |

## Versionamento

[SemVer](https://semver.org/lang/pt-BR/) (`MAIOR.MENOR.PATCH`). Antes da 1.0: `MENOR` para
funcionalidade nova e `PATCH` para correção. Uma versão = uma tag = uma GitHub Release = um milestone. A tag é
o registro permanente da versão (a branch `release/x.y.z` é temporária).
A versão vem só de `src/printroute/version.py` (a esteira a acha pelo `.github/scripts/versao.sh`). As
candidatas usam o sufixo `-rc.N` na tag e no nome do arquivo.
A procedência de qualquer `.exe` gerado pelo CI se verifica com
`gh attestation verify <arquivo>.exe --repo BrunodosSantosVaz/print-route`.

## Configuração do repositório (uma vez)

Feita pelo mantenedor; o passo a passo fica aqui para reprodução em outro repositório:

```bash
# labels, painéis (a conta precisa do escopo "project": gh auth refresh -s project)
scripts/processo/criar-labels.sh  OWNER/REPO
scripts/processo/criar-paineis.sh OWNER/REPO "PrintRoute"
# variáveis (dono e números dos painéis), opções de merge e alertas de segurança
scripts/processo/configurar-automacoes.sh OWNER/REPO N_PLANEJAMENTO N_EXECUCAO N_BUGS
# segredo dos painéis (PAT; veja abaixo)
gh secret set PROJETO_TOKEN --repo OWNER/REPO
```

**`PROJETO_TOKEN`**: o token que o GitHub dá às Actions (`GITHUB_TOKEN`) não enxerga Projects de
usuário, e os eventos gerados por ele não disparam outros workflows. Crie um *Personal Access Token*
(Settings → Developer settings), classic com os escopos `repo` e `project` (o escopo `workflow` só é
preciso se um push da esteira alterar arquivos de `.github/workflows/`), com validade definida.
Ele é usado para mover cartões, criar branches, empurrar a `release/x.y.z` (o que dispara a candidata),
mesclar o PR da release e fazer o back-merge: os últimos passos empurram
em branches protegidas, e o dono é admin e contorna o ruleset.

**Campo Sprint**: painéis novos já nascem com ele (`criar-paineis.sh`). Em painéis que já existem, rode uma vez
`scripts/processo/criar-campo-sprint.sh OWNER N_PLANEJAMENTO N_EXECUCAO N_BUGS` (cria a *Iteration* de 2 semanas e
a mostra nas visões). Novas sprints são acrescentadas em *Settings* do painel → *Sprint*.

**Painel Planejamento**: na interface, desligue *Auto-add sub-issues to project* (vem ligado e traria as
tarefas para dentro do quadro de épicos).

**Proteções**: rulesets em `main` e `develop` exigem pull request, os checks `check` e `regras`, e
bloqueiam force push e exclusão. O ambiente `producao` exige a aprovação do dono e só aceita a `main`.

## Limites conhecidos da automação

- **Um botão novo só existe depois que o workflow está na `main`.** O GitHub só oferece o *Run workflow* de
  arquivos presentes na branch padrão. Ao criar uma etapa nova, ela só passa a poder ser disparada depois do
  merge na `main` (antes disso, apenas por `--ref develop` e só para workflows que já existem na `main`).
- **Cartão movido à mão não dispara nada.** Projects de usuário não emitem eventos: por isso o portão da
  produção **lê o painel** na hora, e *Reprovado* volta pela ação *Criar branches*, não por um evento.
- **PR de fork roda sem segredos.** O Kanban depende do `PROJETO_TOKEN`, que o GitHub não entrega a workflows
  de fork; por isso o cartão de um PR de fora pode não se mover sozinho e o mantenedor o ajusta à mão.
  A integração automática por label também ignora forks (use o botão). Nada disso foi exercitado com um
  fork real.
- **CI do primeiro PR.** O GitHub pode exigir a aprovação do mantenedor antes de rodar o CI do primeiro PR de
  quem é novo no projeto (Settings → Actions → General).
- **Aprovar é humano.** A esteira nunca aprova PR, cartão nem o ambiente `producao` por você.
- **Sem candidata, sem produção.** Sem `vX.Y.Z-rc.N` da versão, ou com o código alterado depois dela, o portão recusa.
