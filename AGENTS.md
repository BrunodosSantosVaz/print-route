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
vazia, `src/printroute/__main__.py`). A arquitetura de captura de impressão (abaixo) já foi decidida pelo
dono; o que falta é implementá-la e validá-la na prática (épico #3).

## Arquitetura de captura de impressão (decidida em 29/09/2026)

Ver a discussão completa na [issue #3](https://github.com/BrunodosSantosVaz/print-route/issues/3),
seção "Riscos e dependências". Resumo: **sem port monitor nativo, sem RedMon** (o mantenedor do RedMon
lista suporte a Windows 10 como "won't be implemented"). Em vez disso, o mesmo princípio do
[PrintManager](https://github.com/jtquisenberry/PrintManager) (AGPL-3.0), mas 100% em Python:

1. **Captura**: observar a pasta de spool do próprio Windows
   (`C:\Windows\System32\spool\PRINTERS`), esperando um `.SPL` novo parar de crescer — mesma
   heurística do protótipo da tarefa #4 (`poc/`), aplicada na pasta de verdade em vez de uma porta
   própria. **Correção (tarefa #6, 29/09/2026)**: a ideia original desta seção era usar
   `win32print.FindFirstPrinterChangeNotification`, mas o **pywin32 não expõe essa função**
   (confirmado no código-fonte de `win32print.cpp` no GitHub — só há `OpenPrinter`, `EnumJobs`,
   `GetJob`, `StartDocPrinter`, `WritePrinter` etc.). Reescrever via `ctypes` chamando a DLL nativa
   diretamente é possível (assinaturas conferidas na documentação da Microsoft), mas foi descartado
   por enquanto: observar a pasta já funciona, é mais simples e reaproveita uma técnica já validada.
   Se isso se mostrar frágil na prática (perder trabalhos concorrentes, por exemplo), reconsidere o
   `ctypes`.
2. **Conversão**: **Ghostscript** (AGPL, binário embutido no instalador) rasteriza/converte o trabalho
   capturado — **ainda não implementado** (tarefa #6 encaminha os bytes brutos, sem conversão; só
   funciona bem quando origem e destino aceitam o mesmo formato, ex.: texto simples). Vira necessário
   de verdade quando a impressora de destino tiver um driver diferente do de origem.
3. **Reenvio**: por enquanto, os bytes brutos vão direto para a impressora de destino via
   `win32print.WritePrinter` (RAW). O ideal (cada impressora recebendo pelo **driver dela própria**,
   via GDI) fica para quando o Ghostscript entrar.

O protótipo da tarefa #4 (`poc/`) foi validado pelo dono num Windows de verdade. A tarefa #6
(`spooler/encaminhar.py`) só foi validada pela CI (Windows real, mas sem um humano conferindo a
impressão de verdade) — quem escreve este código não tem acesso a uma máquina Windows neste ambiente.

## `pyproject.toml` é a referência

Consulte **sempre** o `pyproject.toml` antes de assumir qualquer coisa sobre o projeto:

- **Python mínimo** (`requires-python`): não use recursos de versões mais novas que ele.
- **Versão**: o `pyproject.toml` a lê do `src/printroute/version.py`. Nunca escreva a versão em outro
  lugar, e nunca a altere à mão: é a esteira que sobe a versão ao integrar uma release.
- **Estilo e qualidade**: a configuração do Ruff (`[tool.ruff]`). Rode `uvx ruff check .` no que você mexer.
- **Dependências**: `pywin32` (só Windows, `sys_platform == 'win32'`), usado em
  `spooler/encaminhar.py` (`win32print`: `OpenPrinter`, `StartDocPrinter`, `WritePrinter`, `EnumJobs`,
  `EnumPrinters` etc.) e em `ui/configuracoes.py`. `pystray` + `Pillow` (ícone da bandeja,
  `ui/bandeja.py`) -- cross-platform, sem marcador de SO (mas só usados de fato em código Windows-only).
  `spooler/gerenciar.py` e `inicializacao.py` continuam só com `subprocess`/`winreg`, sem pywin32. CI
  roda `pip install -e .` antes dos testes nos jobs `check`/`compat` (windows-latest). A dependência de
  build (o PyInstaller) fica **só** no `requirements-build.txt`. Não a duplique no `pyproject.toml`.
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
| `src/printroute/spooler/` | Interação com o spooler: `gerenciar.py` (instala/remove a impressora, via PowerShell), `encaminhar.py` (captura pela pasta de spool + reenvio bruto, via `pywin32`). Testes só rodam no Windows (`check`/`compat` na CI). |
| `src/printroute/configuracao.py` | Impressoras de destino, cópias e modo (fixo/perguntar), em JSON. Sem dependência do Windows: testes rodam em qualquer sistema. |
| `src/printroute/selecao.py` | Lógica do seletor de impressora na hora (modo "perguntar"): candidatas, escolha padrão, validação. Sem Tkinter, testável em qualquer sistema. |
| `src/printroute/estado.py` | Se o reencaminhamento está ativado/pausado (em memória, menu da bandeja). Testável em qualquer sistema. |
| `src/printroute/inicializacao.py` | Iniciar o PrintRoute com o Windows (chave Run do Registro, via `winreg`). Testes só rodam no Windows. |
| `src/printroute/ui/` | Telas (Tkinter/`pystray`): `seletor.py` (usa `selecao.py`), `configuracoes.py` (usa `configuracao.py` e `inicializacao.py`), `bandeja.py` (o ícone e o menu, usa `estado.py`). **Sem teste automatizado** (interface gráfica/bandeja, precisa de display) -- só a lógica por trás é testada. |
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

- Mudar a arquitetura de captura de impressão já decidida (veja
  [Arquitetura de captura de impressão](#arquitetura-de-captura-de-impressão-decidida-em-29092026)) sem
  discutir com o dono, ou registrar um port monitor, driver ou serviço no Windows fora dessa arquitetura.
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
