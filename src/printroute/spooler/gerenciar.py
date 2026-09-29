"""Instala e remove a impressora PrintRoute no Windows: a porta local (arquivo) e a
impressora em si. Usa os cmdlets do PowerShell (Add-PrinterPort, Add-Printer,
Remove-Printer, Remove-PrinterPort) em vez da API Win32 de baixo nível: são a forma
documentada e estável de gerenciar impressoras no Windows, e evitam lidar diretamente
com as estruturas PRINTER_INFO_2 da API nativa. O driver "Generic / Text Only" é o
mesmo usado no protótipo da tarefa #4 (poc/), já validado pelo dono; a tarefa #3
(encaminhar de verdade) deve revisitar essa escolha ao integrar o Ghostscript.

Ver AGENTS.md, seção "Arquitetura de captura de impressão", e a tarefa #5 do épico #3.
"""
import base64
import subprocess

NOME_IMPRESSORA = "PrintRoute"
PASTA_DADOS = r"C:\ProgramData\PrintRoute"
CAMINHO_PORTA = PASTA_DADOS + r"\trabalho.spl"
NOME_DRIVER = "Generic / Text Only"

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
    # -ErrorAction SilentlyContinue (confirmado na CI: Get-PrinterPort "não encontrado",
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
    )
    saida = resultado.stdout.strip()
    if saida.startswith(_MARCADOR_DE_ERRO):
        raise ErroDoPowerShell(saida[len(_MARCADOR_DE_ERRO) :].strip())
    return saida


def porta_existe() -> bool:
    saida = _powershell(
        f"Get-PrinterPort -Name '{CAMINHO_PORTA}' -ErrorAction SilentlyContinue | ConvertTo-Json -Compress"
    )
    return bool(saida)


def impressora_existe() -> bool:
    saida = _powershell(
        f"Get-Printer -Name '{NOME_IMPRESSORA}' -ErrorAction SilentlyContinue | ConvertTo-Json -Compress"
    )
    return bool(saida)


def instalar() -> None:
    """Cria a pasta de dados, a porta e a impressora PrintRoute. Repetir a chamada não
    duplica nada (idempotente)."""
    _powershell(f"New-Item -ItemType Directory -Path '{PASTA_DADOS}' -Force | Out-Null")
    if not porta_existe():
        _powershell(f"Add-PrinterPort -Name '{CAMINHO_PORTA}'")
    if not impressora_existe():
        _powershell(f"Add-Printer -Name '{NOME_IMPRESSORA}' -DriverName '{NOME_DRIVER}' -PortName '{CAMINHO_PORTA}'")


def desinstalar() -> None:
    """Remove a impressora e a porta PrintRoute. Não falha se algum dos dois já não
    existir (idempotente)."""
    _powershell(f"Remove-Printer -Name '{NOME_IMPRESSORA}' -ErrorAction SilentlyContinue")
    _powershell(f"Remove-PrinterPort -Name '{CAMINHO_PORTA}' -ErrorAction SilentlyContinue")


def main() -> None:
    import sys

    if len(sys.argv) != 2 or sys.argv[1] not in ("instalar", "desinstalar", "status"):
        print("Uso: python -m printroute.spooler.gerenciar instalar|desinstalar|status")
        raise SystemExit(2)

    acao = sys.argv[1]
    if acao == "instalar":
        instalar()
        print(f"Impressora '{NOME_IMPRESSORA}' instalada (porta: {CAMINHO_PORTA}).")
    elif acao == "desinstalar":
        desinstalar()
        print(f"Impressora '{NOME_IMPRESSORA}' removida.")
    else:
        print(f"Porta existe: {porta_existe()}")
        print(f"Impressora existe: {impressora_existe()}")


if __name__ == "__main__":
    main()
