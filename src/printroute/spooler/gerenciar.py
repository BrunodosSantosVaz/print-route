"""Instala e remove a impressora PrintRoute no Windows. Usa os cmdlets do PowerShell
(Add-Printer, Remove-Printer) em vez da API Win32 de baixo nível: são a forma
documentada e estável de gerenciar impressoras no Windows, e evitam lidar com as
estruturas PRINTER_INFO_2 da API nativa.

A impressora usa uma porta que **já existe** no Windows (ver CANDIDATOS_DE_PORTA) em vez
de uma porta própria criada e removida por este módulo. É proposital: a arquitetura de
captura decidida (ver AGENTS.md, "Arquitetura de captura de impressão") lê o trabalho
pelo FindFirstPrinterChangeNotification e pela pasta de spool do próprio Windows, não
pelo que a porta grava, então a porta só precisa existir e "completar" o trabalho sem
travar a fila -- qualquer porta já presente serve, sem exigir criação nem remoção. Isso
também evitou um problema real: tentei antes uma porta local (arquivo) e nem
`Remove-PrinterPort` (dois formatos) nem `rundll32 printui.dll` nem `win32print`
(que nem expõe DeletePort) conseguiram removê-la de forma confiável na CI -- histórico
completo nos commits desta tarefa. Nem toda porta "clássica" existe em toda instalação
(confirmado na CI: nem "NUL:" vem por padrão no Windows Server dos runners), por isso a
porta, como o driver, é escolhida em tempo de execução, com uma lista de candidatos e,
faltando todos, a primeira porta que o sistema realmente tiver.

O driver é escolhido do mesmo jeito, em tempo de execução entre alguns candidatos já
instalados no Windows (ver CANDIDATOS_DE_DRIVER): "Generic / Text Only", validado no
protótipo da tarefa #4 (poc/), não existe por padrão no Windows Server usado pelos
runners da CI (confirmado por um teste que falhou), então não dá para fixar um nome só.
A tarefa #3 (encaminhar de verdade) deve revisitar essa escolha ao integrar o
Ghostscript.

Ver AGENTS.md, seção "Arquitetura de captura de impressão", e a tarefa #5 do épico #3.
"""
import base64
import json
import subprocess

NOME_IMPRESSORA = "PrintRoute"

# Ordem de preferência: a primeira já instalada no Windows é usada; sem nenhuma das
# listadas, cai para a primeira porta que o `Get-PrinterPort` encontrar (ver
# _escolher_porta) -- confirmado na CI que nem "NUL:" é garantida (Windows Server).
CANDIDATOS_DE_PORTA = ("NUL:", "FILE:", "LPT1:", "COM1:")

# Ordem de preferência: o primeiro já instalado no Windows é usado. "Generic / Text
# Only" é o do protótipo da tarefa #4 (Windows cliente); os outros são drivers
# virtuais que também costumam vir com o Windows (cliente e Server), usados como
# alternativa em máquinas sem o primeiro (ex.: os runners da CI).
CANDIDATOS_DE_DRIVER = (
    "Generic / Text Only",
    "Microsoft Print To PDF",
    "Microsoft XPS Document Writer v4",
    "Microsoft XPS Document Writer",
)

_MARCADOR_DE_ERRO = "ERRO_POWERSHELL:"


class ErroDoPowerShell(RuntimeError):
    """Um cmdlet do PowerShell terminou com erro; a mensagem vem de $_.Exception.Message,
    capturada dentro do próprio script (ver _powershell)."""


def _powershell(comando: str) -> str:
    # -EncodedCommand (Base64 de UTF-16LE) em vez de -Command com a string crua: evita
    # qualquer ambiguidade de aspas/pipe ao montar a linha de comando pelo subprocess no
    # Windows. -ExecutionPolicy Bypass: sem isso, o carregamento automático do módulo
    # PrintManagement (módulo de script, não binário) pode ser bloqueado pela política de
    # execução do Windows.
    #
    # O sinal de falha é o marcador escrito pelo catch, NUNCA o código de saída do
    # processo: o powershell.exe clássico pode voltar 1 mesmo sem nenhuma exceção, só
    # por ter havido um erro não-terminante internamente suprimido por
    # -ErrorAction SilentlyContinue (confirmado na CI: Get-Printer "não encontrado",
    # um resultado válido e esperado, às vezes sai com código 1 mesmo assim).
    script = (
        "$ErrorActionPreference = 'Stop'\n"
        "try {\n"
        f"{comando}\n"
        "} catch {\n"
        f"  Write-Output ('{_MARCADOR_DE_ERRO} ' + $_.Exception.Message)\n"
        "}\n"
    )
    codificado = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    resultado = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-EncodedCommand", codificado],
        capture_output=True,
        text=True,
        # Sem isso, uma janela de console do powershell.exe aparece na tela a cada
        # chamada -- e gerenciar.instalar() roda em TODA abertura do PrintRoute
        # (--windowed não impede um processo FILHO de linha de comando de abrir a
        # própria janela). Bug real, achado ao vivo (tarefa #38; mesma causa raiz da
        # tarefa #36, lá só corrigida no Ghostscript).
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    saida = resultado.stdout.strip()
    if saida.startswith(_MARCADOR_DE_ERRO):
        raise ErroDoPowerShell(saida[len(_MARCADOR_DE_ERRO) :].strip())
    return saida


def impressora_existe() -> bool:
    saida = _powershell(
        f"Get-Printer -Name '{NOME_IMPRESSORA}' -ErrorAction SilentlyContinue | ConvertTo-Json -Compress"
    )
    return bool(saida)


def _escolher_driver() -> str:
    for nome in CANDIDATOS_DE_DRIVER:
        saida = _powershell(
            f"Get-PrinterDriver -Name '{nome}' -ErrorAction SilentlyContinue | ConvertTo-Json -Compress"
        )
        if saida:
            return nome
    raise ErroDoPowerShell("Nenhum driver candidato está instalado: " + ", ".join(CANDIDATOS_DE_DRIVER))


def _escolher_porta() -> str:
    """Bug real (achado testando o instalador num Windows 11 de verdade, não só na CI): o
    Windows não garante a caixa das portas clássicas -- aqui `Get-PrinterPort` devolve
    "nul:" (minúsculo), não "NUL:". A comparação exata contra CANDIDATOS_DE_PORTA nunca
    batia, então a escolha caía para "FILE:" -- que pede um caminho toda vez que alguém
    imprime (a mesma causa do "Print to File..." clássico do Windows), travando o trabalho
    antes mesmo dele terminar de ser gravado no spool. Por isso a comparação é
    case-insensitive, mas o nome DEVOLVIDO é sempre o que o sistema realmente tem (nunca o
    literal de CANDIDATOS_DE_PORTA), porque Add-Printer precisa do nome exato cadastrado."""
    saida = _powershell("Get-PrinterPort | Select-Object -ExpandProperty Name | ConvertTo-Json -Compress")
    nomes = json.loads(saida) if saida else []
    if isinstance(nomes, str):
        nomes = [nomes]
    por_nome_normalizado = {nome.upper(): nome for nome in nomes}
    for candidato in CANDIDATOS_DE_PORTA:
        if candidato.upper() in por_nome_normalizado:
            return por_nome_normalizado[candidato.upper()]
    if nomes:
        return nomes[0]
    raise ErroDoPowerShell("Nenhuma porta de impressora disponível no sistema.")


def instalar() -> None:
    """Cria a impressora PrintRoute (numa porta já existente no sistema, ver
    CANDIDATOS_DE_PORTA). Repetir a chamada não duplica nada (idempotente)."""
    if not impressora_existe():
        driver = _escolher_driver()
        porta = _escolher_porta()
        _powershell(f"Add-Printer -Name '{NOME_IMPRESSORA}' -DriverName '{driver}' -PortName '{porta}'")


def desinstalar() -> None:
    """Remove a impressora PrintRoute. Não falha se ela já não existir (idempotente).
    Não mexe em porta nenhuma: usa uma porta já existente no sistema, nunca criada nem
    removida por aqui."""
    _powershell(f"Remove-Printer -Name '{NOME_IMPRESSORA}' -ErrorAction SilentlyContinue")


def main() -> None:
    import sys

    if len(sys.argv) != 2 or sys.argv[1] not in ("instalar", "desinstalar", "status"):
        print("Uso: python -m printroute.spooler.gerenciar instalar|desinstalar|status")
        raise SystemExit(2)

    acao = sys.argv[1]
    if acao == "instalar":
        instalar()
        print(f"Impressora '{NOME_IMPRESSORA}' instalada.")
    elif acao == "desinstalar":
        desinstalar()
        print(f"Impressora '{NOME_IMPRESSORA}' removida.")
    else:
        print(f"Impressora existe: {impressora_existe()}")


if __name__ == "__main__":
    main()
