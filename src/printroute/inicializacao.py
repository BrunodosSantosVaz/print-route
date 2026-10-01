"""Iniciar o PrintRoute com o Windows: cria uma Tarefa Agendada (Task Scheduler) que
roda no login do usuário atual, já elevada ("Executar com os privilégios mais altos"),
sem pedir confirmação do UAC a cada vez.

**Não** usa a chave Run do Registro (`HKEY_CURRENT_USER\\...\\Run`, o jeito mais simples
-- e o que este módulo usava até a tarefa #38): desde que o `PrintRoute.exe` passou a
exigir elevação (`--uac-admin`, tarefa #30 -- a pasta de spool do Windows só é legível
por um processo elevado), um programa na chave Run que precise de elevação é conhecido
por não iniciar de forma confiável no login (o Windows nem sempre consegue mostrar o
prompt do UAC nesse momento, sem uma sessão interativa já pronta, e sem resposta o
processo simplesmente não abre) -- bug real, achado ao vivo (tarefa #38): "não ta
vindo na bandeja". A Tarefa Agendada com "Executar com os privilégios mais altos" é a
forma documentada pela própria Microsoft de contornar isso: o Agendador de Tarefas tem
seu próprio mecanismo de elevação, que não depende do prompt interativo do UAC no
momento do login, e não pede senha (roda como o usuário atual, só quando ele já está
logado -- o padrão do `schtasks /Create` sem `/RU`).

Usa `schtasks.exe` (sempre disponível no Windows, linha de comando) em vez de alguma
biblioteca de Task Scheduler: evita mais uma dependência nova, e seguimos o mesmo
padrão já usado em `spooler/gerenciar.py` (cmdlets/utilitários de linha de comando via
`subprocess`, não a API nativa direto)."""
import subprocess

NOME_DA_TAREFA = "PrintRoute"


def _schtasks(*args: str) -> subprocess.CompletedProcess:
    # creationflags: mesma razão da tarefa #38 em gerenciar.py -- sem isso, uma janela
    # de console do schtasks.exe apareceria na tela ao marcar/desmarcar a opção nas
    # configurações.
    return subprocess.run(
        ["schtasks", *args],
        capture_output=True,
        text=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def esta_habilitado() -> bool:
    return _schtasks("/Query", "/TN", NOME_DA_TAREFA).returncode == 0


def habilitar(caminho_do_executavel: str) -> None:
    """Cria (ou substitui, `/F`) a tarefa agendada. Repetir a chamada é idempotente."""
    resultado = _schtasks(
        "/Create", "/TN", NOME_DA_TAREFA, "/TR", f'"{caminho_do_executavel}"',
        "/SC", "ONLOGON", "/RL", "HIGHEST", "/F",
    )
    if resultado.returncode != 0:
        raise RuntimeError(f"schtasks /Create falhou: {resultado.stderr.strip() or resultado.stdout.strip()}")


def desabilitar() -> None:
    """Remove a tarefa agendada. Não falha se ela já não existir (idempotente)."""
    if esta_habilitado():
        _schtasks("/Delete", "/TN", NOME_DA_TAREFA, "/F")
