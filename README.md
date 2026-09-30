# PrintRoute

**Uma impressora virtual que reencaminha.** O PrintRoute aparece no Windows como mais uma impressora.
Quando um programa manda imprimir nela, ele encaminha a impressão para uma ou mais impressoras reais —
pré-configuradas, ou escolhidas na hora, num seletor. Pensado para sistemas que só permitem configurar
**uma** impressora: a virtual entra no lugar dela e decide para onde a impressão vai de verdade.

[![CI](https://github.com/BrunodosSantosVaz/print-route/actions/workflows/ci.yml/badge.svg)](https://github.com/BrunodosSantosVaz/print-route/actions/workflows/ci.yml)
[![Licença AGPL-3.0](https://img.shields.io/badge/licen%C3%A7a-AGPL--3.0-blue)](LICENSE)
![Plataforma](https://img.shields.io/badge/plataforma-Windows%2010%2F11-lightgrey)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Status](https://img.shields.io/badge/status-em%20desenvolvimento-orange)

## Estado atual

**Em desenvolvimento, sem release publicada ainda.** A captura, o reencaminhamento (uma ou mais
impressoras, com cópias, reconstruindo o documento pelo driver de cada uma via Ghostscript), o seletor
na hora, a configuração, o ícone na bandeja e o instalador (com desinstalador e elevação automática) já
existem e foram testados numa sessão de desktop real, não só pela CI (veja
[épico #3](https://github.com/BrunodosSantosVaz/print-route/issues/3)). Até a primeira versão ser
publicada, não há nada nas [Releases](https://github.com/BrunodosSantosVaz/print-route/releases) para
baixar.

## Para que serve

Muitos sistemas legados ou parametrizáveis só permitem configurar **uma** impressora de saída (boletos,
etiquetas, comprovantes...). Quando a impressão precisa ir para mais de um lugar, ou o destino muda
conforme a situação, a única saída costuma ser reconfigurar o sistema toda vez. O PrintRoute resolve
isso por fora: ele se registra como uma impressora comum, então qualquer programa pode "imprimir" nele
sem saber que existe um roteamento por trás. O que acontece depois:

- **Reencaminhar para uma ou mais impressoras pré-configuradas**, sem intervenção.
- **Abrir um seletor na hora**, para escolher a impressora de destino a cada impressão.

## Como usar

Ainda não há nada para usar: veja [Estado atual](#estado-atual). Esta seção será escrita quando a
primeira funcionalidade de reencaminhamento existir.

## Para desenvolvedores

### Estrutura do repositório

```
print-route/
├── src/printroute/                 Código-fonte (pacote Python)
│   ├── __main__.py                  Ponto de entrada (python -m printroute); liga tudo abaixo
│   ├── version.py                   Versão do programa
│   ├── configuracao.py              Impressoras de destino, cópias e modo (JSON)
│   ├── selecao.py                   Lógica do seletor de impressora na hora
│   ├── estado.py                    Reencaminhamento ativado/pausado (em memória)
│   ├── inicializacao.py             Iniciar com o Windows (Registro, winreg)
│   ├── spooler/                     gerenciar.py (instala/remove a impressora), encaminhar.py (captura + reenvio)
│   └── ui/                          Telas: seletor.py, configuracoes.py, bandeja.py (ícone + menu)
├── tests/                          Testes automatizados (unittest), inclusive dos scripts da esteira
├── packaging/windows/               build_exe.py (compila o .exe) e build_installer.py + instalador.iss
│                                    (empacotam o instalador Windows, via Inno Setup); saem do CI
├── scripts/processo/               Configuração do GitHub (labels, painéis, automações)
├── docs/processo.md                Processo de desenvolvimento completo
├── .github/                        Workflows (CI, build, release), modelos de issue/PR, automações
├── pyproject.toml                  Metadados do projeto, versão (lida de src/printroute/version.py) e Ruff
├── requirements-build.txt          Dependência de build (PyInstaller)
├── AGENTS.md, CLAUDE.md            Instruções para IAs que trabalham no projeto
└── CHANGELOG.md, CONTRIBUTING.md, SECURITY.md, CODE_OF_CONDUCT.md, LICENSE
```

### Rodando a partir do código-fonte

Requer **Python 3.10 ou superior com Tkinter** (o instalador oficial do Python para Windows já inclui).
Nenhuma biblioteca externa é necessária para rodar o esqueleto atual.

```powershell
git clone https://github.com/BrunodosSantosVaz/print-route.git
cd print-route
python src\printroute\__main__.py
```

Ou instale o projeto para desenvolver (`pip install -e .`) e rode `python -m printroute`.

### Testes

```powershell
python -m unittest discover -s tests -v
uvx ruff check .          # estilo e qualidade (regras em pyproject.toml); ou: pip install ruff && ruff check .
```

Roda a cada pull request no GitHub Actions (Windows), junto com o Ruff.

### Gerando o instalador

Requer também o [Inno Setup 6](https://jrsoftware.org/isinfo.php) (`ISCC.exe` em PATH, ou em
`C:\Program Files (x86)\Inno Setup 6\`; `choco install innosetup` instala).

```powershell
pip install -r requirements-build.txt
python packaging\windows\build_installer.py
```

O script compila com PyInstaller (fora do repositório, sem deixar `build/` ou `.spec`) e empacota o
resultado com o Inno Setup (`packaging/windows/instalador.iss`), gravando o instalador e o
`SHA256SUMS.txt` em `build-local/` (ignorada pelo Git). A versão vem de `src/printroute/version.py`.
Os instaladores **oficiais** (candidatas e produção) são gerados pelo CI e publicados nas Releases,
não à mão. `python packaging\windows\build_exe.py` sozinho ainda compila só o `.exe` puro (sem
instalador), útil para testar rápido sem empacotar.

## Versões e releases

O projeto usa [versionamento semântico](https://semver.org/lang/pt-BR/) (`MAIOR.MENOR.PATCH`) e cada
versão é registrada no [CHANGELOG](CHANGELOG.md). Antes da 1.0, `MENOR` sobe com funcionalidade nova e
`PATCH` com correção. **A versão diz o ambiente**, e o executável fica na página de
[Releases](https://github.com/BrunodosSantosVaz/print-route/releases) (nenhuma publicada ainda). O ciclo
completo (planejamento, testes, build no CI, aprovação e publicação) está em
[docs/processo.md](docs/processo.md).

## Segurança

O PrintRoute vai precisar falar com o spooler de impressão do Windows (portas, impressoras, drivers), o
que é uma superfície diferente de um programa só de leitura local. Veja a
[política de segurança](SECURITY.md) para o que é considerado vulnerabilidade e como relatar.

## Contribuindo

O PrintRoute é open source (licença AGPL-3.0) e aceita contribuição de qualquer pessoa: uma pergunta, um
problema encontrado ou uma alteração no código. Como o projeto está no início, a forma mais útil de
ajudar agora é discutir a arquitetura (veja [Discussions](https://github.com/BrunodosSantosVaz/print-route/discussions)).

| Quero… | Vá para | Observação |
|--------|---------|------------|
| Tirar uma dúvida ou discutir a arquitetura | [Discussions](https://github.com/BrunodosSantosVaz/print-route/discussions) → **Q&A** | Conversa: não vira issue |
| Sugerir uma ideia | [Discussions](https://github.com/BrunodosSantosVaz/print-route/discussions) → **Ideas** | Se amadurecer, o mantenedor a transforma em épico |
| Relatar um bug | [Nova issue](https://github.com/BrunodosSantosVaz/print-route/issues/new/choose) → formulário **Bug** | Informe versão, passos para reproduzir e resultado esperado × obtido |
| Alterar o código, a documentação ou os testes | **Pull request** a partir de um fork | Sempre para a branch `develop`, ligado a uma issue |
| Relatar uma vulnerabilidade | [Relato privado](https://github.com/BrunodosSantosVaz/print-route/security/advisories/new) | Nunca em issue pública ([SECURITY.md](SECURITY.md)) |

O passo a passo detalhado está em [CONTRIBUTING.md](CONTRIBUTING.md), o processo completo em
[docs/processo.md](docs/processo.md) e a conduta esperada no [Código de Conduta](CODE_OF_CONDUCT.md).

## Licença e avisos

Distribuído sob a **[Licença AGPL-3.0](LICENSE)**. O software é fornecido "como está", sem garantia.

O `.exe`, quando publicado, empacotará o interpretador **Python** (licença PSF), o **Tcl/Tk** (licença
BSD) e será gerado com o **PyInstaller** (GPLv2 com exceção que permite distribuir o executável gerado
sob a licença do seu próprio programa). O instalador também embute o **Ghostscript/`ghostxps`**
([Artifex](https://www.ghostscript.com/), AGPL-3.0 — mesma licença do PrintRoute), usado para reconstruir
o documento capturado na impressora de destino.
