"""Instala e remove a impressora PrintRoute no Windows: a porta local (arquivo) e a
impressora em si. Usa sobretudo os cmdlets do PowerShell (Add-PrinterPort, Add-Printer,
Remove-Printer) em vez da API Win32 de baixo nível diretamente: são a forma documentada
e estável de gerenciar impressoras no Windows, e evitam lidar com as estruturas
PRINTER_INFO_2 da API nativa. A exceção é remover a porta, feita com
`win32print.DeletePort` (pywin32): os cmdlets equivalentes (Remove-PrinterPort e
rundll32 printui.dll) falharam de verdade na CI para um nome de porta com barra
invertida -- ver o docstring de `desinstalar`. O driver é escolhido em tempo de execução
entre alguns candidatos já instalados no Windows (ver CANDIDATOS_DE_DRIVER):
"Generic / Text Only", validado no protótipo da tarefa #4 (poc/), não existe por padrão
no Windows Server usado pelos runners da CI (confirmado por um teste que falhou), então
não dá para fixar um nome só. A tarefa #3 (encaminhar de verdade) deve revisitar essa
escolha ao integrar o Ghostscript.

Ver AGENTS.md, seção "Arquitetura de captura de impressão", e a tarefa #5 do épico #3.
"""
import base64
import contextlib
import subprocess
import time

import pywintypes
import win32print

NOME_IMPRESSORA = "PrintRoute"
PASTA_DADOS = r"C:\ProgramData\PrintRoute"
CAMINHO_PORTA = PASTA_DADOS + r"\trabalho.spl"

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


def _escolher_driver() -> str:
    for nome in CANDIDATOS_DE_DRIVER:
        saida = _powershell(
            f"Get-PrinterDriver -Name '{nome}' -ErrorAction SilentlyContinue | ConvertTo-Json -Compress"
        )
        if saida:
            return nome
    raise ErroDoPowerShell("Nenhum driver candidato está instalado: " + ", ".join(CANDIDATOS_DE_DRIVER))


def instalar() -> None:
    """Cria a pasta de dados, a porta e a impressora PrintRoute. Repetir a chamada não
    duplica nada (idempotente)."""
    _powershell(f"New-Item -ItemType Directory -Path '{PASTA_DADOS}' -Force | Out-Null")
    if not porta_existe():
        _powershell(f"Add-PrinterPort -Name '{CAMINHO_PORTA}'")
    if not impressora_existe():
        driver = _escolher_driver()
        _powershell(f"Add-Printer -Name '{NOME_IMPRESSORA}' -DriverName '{driver}' -PortName '{CAMINHO_PORTA}'")


def desinstalar() -> None:
    """Remove a impressora e a porta PrintRoute. Não falha se nenhuma das duas existir
    (idempotente). Tenta remover a porta algumas vezes: o spooler pode levar um instante
    para soltá-la depois de remover a impressora que a usava (confirmado na CI: a
    primeira tentativa, logo após Remove-Printer, às vezes não é suficiente).

    A remoção da porta usa `win32print.DeletePort` (pywin32, a API Win32 direta), não um
    cmdlet do PowerShell: `Remove-PrinterPort -Name '<caminho>'`,
    `Get-PrinterPort | Remove-PrinterPort` e `rundll32 printui.dll,PrintUIEntry /dl`
    falharam todos, confirmado na CI -- os dois primeiros com "Names may not contain ','
    or '\\' characters" (uma limitação conhecida desses cmdlets com nomes de porta que
    têm barra invertida) e o terceiro silenciosamente (não é confiável sem uma sessão
    interativa). A API `DeletePort` não tem essa validação."""
    _powershell(f"Remove-Printer -Name '{NOME_IMPRESSORA}' -ErrorAction SilentlyContinue")
    for tentativa in range(10):
        if not porta_existe():
            return
        if tentativa:
            time.sleep(1)
        with contextlib.suppress(pywintypes.error):
            win32print.DeletePort(None, 0, CAMINHO_PORTA)
    if porta_existe():
        raise ErroDoPowerShell(f"Não consegui remover a porta '{CAMINHO_PORTA}' depois de várias tentativas.")


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
