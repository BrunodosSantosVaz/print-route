"""Gera o instalador Windows do PrintRoute: compila o .exe (build_exe.py) e o empacota
com o Inno Setup (instalador.iss) num único instalador, com atalho no Menu Iniciar,
registro em Configurações > Aplicativos e desinstalador de verdade -- tarefa #11.

    python packaging/windows/build_installer.py                    # build-local/
    python packaging/windows/build_installer.py --rc 2 --saida rc  # release candidata

Requer, além do que build_exe.py já precisa, o compilador do Inno Setup (ISCC.exe) --
normalmente em "C:\\Program Files (x86)\\Inno Setup 6\\ISCC.exe", ou já em PATH. Os
instaladores oficiais (candidatas e produção) são gerados pelo CI (workflow "Build
release candidata"), que instala o Inno Setup antes de chamar este script.

Resultado, na pasta de saída:
    PrintRoute-Setup-v<versão>[-rc.N]-windows-x64.exe
    SHA256SUMS.txt
"""
import argparse
import os
import shutil
import subprocess

import build_exe

RAIZ = build_exe.RAIZ
PASTA_PACKAGING = os.path.dirname(os.path.abspath(__file__))
ISCC_CANDIDATOS = (
    "ISCC.exe",  # já em PATH (ex.: instalado via choco)
    r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    r"C:\Program Files\Inno Setup 6\ISCC.exe",
)


def _achar_iscc() -> str:
    for candidato in ISCC_CANDIDATOS:
        if shutil.which(candidato) or os.path.isfile(candidato):
            return candidato
    raise FileNotFoundError(
        "ISCC.exe (compilador do Inno Setup) não encontrado. Instale o Inno Setup 6 "
        "(https://jrsoftware.org/isinfo.php ou 'choco install innosetup') e tente de novo."
    )


def nome_do_instalador(rc=None) -> str:
    """Nome do instalador: PrintRoute-Setup-v0.1.0-windows-x64.exe (produção) ou
    PrintRoute-Setup-v0.1.0-rc.1-windows-x64.exe (candidata)."""
    sufixo = f"-rc.{int(rc)}" if rc else ""
    return f"PrintRoute-Setup-v{build_exe.__version__}{sufixo}-windows-x64.exe"


def sha256(caminho: str) -> str:
    return build_exe.sha256(caminho)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compila o PrintRoute e empacota o instalador Windows.")
    parser.add_argument("--saida", help="pasta de destino (padrão: build-local/)")
    parser.add_argument("--rc", type=int, help="número da release candidata (vira -rc.N no nome do instalador)")
    args = parser.parse_args()

    iscc = _achar_iscc()
    destino_pasta = os.path.abspath(args.saida) if args.saida else os.path.join(RAIZ, "build-local")
    os.makedirs(destino_pasta, exist_ok=True)

    # 1. Compila o .exe puro (sem o sufixo -rc.N/versão no nome: só o instalador leva
    #    esse nome público; o .exe embutido dentro dele pode ter um nome simples fixo).
    exe_bruto = os.path.join(destino_pasta, "PrintRoute.exe")
    build_exe.compilar(exe_bruto)

    # 2. Empacota com o Inno Setup.
    nome_final = nome_do_instalador(args.rc)
    for antigo in os.listdir(destino_pasta):  # nunca deixar instalador/hash de builds anteriores misturados
        if antigo.startswith("PrintRoute-Setup-") or antigo == "SHA256SUMS.txt":
            os.remove(os.path.join(destino_pasta, antigo))
    cmd = [
        iscc,
        f"/DMyAppVersion={build_exe.__version__}",
        f"/DMyAppExe={exe_bruto}",
        f"/DMyOutputDir={destino_pasta}",
        f"/DMyOutputBaseFilename={nome_final[:-4]}",  # sem a extensão .exe (o Inno Setup a acrescenta)
        os.path.join(PASTA_PACKAGING, "instalador.iss"),
    ]
    print(" ".join(cmd))
    subprocess.run(cmd, check=True)

    final = os.path.join(destino_pasta, nome_final)
    if not os.path.isfile(final):
        raise FileNotFoundError(f"O Inno Setup não gerou o arquivo esperado: {final}")
    os.remove(exe_bruto)  # só o instalador é publicado; o .exe bruto era um passo intermediário

    with open(os.path.join(destino_pasta, "SHA256SUMS.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write(f"{sha256(final)}  {nome_final}\n")
    print(f"\nOK: {os.path.relpath(final, RAIZ)}  ({os.path.getsize(final) / 1e6:.1f} MB)")
    print(f"SHA-256: {sha256(final)}")


if __name__ == "__main__":
    main()
