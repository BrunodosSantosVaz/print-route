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
import hashlib
import os
import shutil
import subprocess
import zipfile
from urllib.request import urlretrieve

import build_exe

RAIZ = build_exe.RAIZ
PASTA_PACKAGING = os.path.dirname(os.path.abspath(__file__))
ISCC_CANDIDATOS = (
    "ISCC.exe",  # já em PATH (ex.: instalado via choco)
    r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    r"C:\Program Files\Inno Setup 6\ISCC.exe",
)

# Ghostscript/ghostxps: lê o pacote XPS capturado e reconstrói na impressora de destino
# pelo driver dela própria (ver src/printroute/spooler/encaminhar.py, tarefa #34).
# É o binário separado do "gs" principal (esse não lê XPS sozinho) -- versão fixa (não
# "latest"), com hash conferido, pela mesma razão do PyInstaller/Inno Setup: build
# reprodutível e à prova de adulteração no meio do caminho.
GHOSTXPS_VERSAO = "10.08.0"
GHOSTXPS_URL = (
    "https://github.com/ArtifexSoftware/ghostpdl-downloads/releases/download/"
    f"gs10080/ghostxps-{GHOSTXPS_VERSAO}-win64.zip"
)
GHOSTXPS_SHA512 = (
    "2251f6c3e49408c931c3c050310e8fd612d9e19ca3c6c1b697068a76320a0ee"
    "3a9839d84fd2e06fd80923264c57b429a234909b717e05efae99ee5202bf835ab"
)
GHOSTXPS_ARQUIVOS = ("gxpswin64.exe", "gxpsdll64.dll")


def _achar_iscc() -> str:
    for candidato in ISCC_CANDIDATOS:
        if shutil.which(candidato) or os.path.isfile(candidato):
            return candidato
    raise FileNotFoundError(
        "ISCC.exe (compilador do Inno Setup) não encontrado. Instale o Inno Setup 6 "
        "(https://jrsoftware.org/isinfo.php ou 'choco install innosetup') e tente de novo."
    )


def _preparar_ghostxps(pasta_cache: str) -> str:
    """Baixa (se ainda não estiver em cache) e confere o hash do ghostxps, e devolve a
    pasta com gxpswin64.exe + gxpsdll64.dll prontos para o Inno Setup embutir no
    instalador. `PRINTROUTE_GHOSTXPS_DIR` sobrescreve com uma pasta já pronta (sem
    baixar nada) -- útil offline ou com um cache próprio no CI."""
    de_ambiente = os.environ.get("PRINTROUTE_GHOSTXPS_DIR")
    if de_ambiente:
        return de_ambiente

    os.makedirs(pasta_cache, exist_ok=True)
    if all(os.path.isfile(os.path.join(pasta_cache, nome)) for nome in GHOSTXPS_ARQUIVOS):
        return pasta_cache

    zip_caminho = os.path.join(pasta_cache, "ghostxps.zip")
    print(f"Baixando o Ghostscript/ghostxps {GHOSTXPS_VERSAO}...")
    urlretrieve(GHOSTXPS_URL, zip_caminho)

    h = hashlib.sha512()
    with open(zip_caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1024 * 1024), b""):
            h.update(bloco)
    if h.hexdigest() != GHOSTXPS_SHA512:
        os.remove(zip_caminho)
        raise ValueError(
            "SHA-512 do ghostxps baixado não bate com o esperado -- download "
            "corrompido ou adulterado no meio do caminho. Build abortado."
        )

    with zipfile.ZipFile(zip_caminho) as z:
        prefixo = f"ghostxps-{GHOSTXPS_VERSAO}-win64/"
        for nome in GHOSTXPS_ARQUIVOS:
            with z.open(prefixo + nome) as origem, open(os.path.join(pasta_cache, nome), "wb") as destino:
                shutil.copyfileobj(origem, destino)
    os.remove(zip_caminho)
    return pasta_cache


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

    # 1b. Ghostxps (lê o XPS capturado -- ver encaminhar.py, tarefa #34): cache fixo,
    #     fora da pasta de saída (que varia por --saida), pra não baixar de novo a
    #     cada build.
    pasta_ghostxps = _preparar_ghostxps(os.path.join(RAIZ, "build-local", "ghostxps-cache"))

    # 2. Empacota com o Inno Setup.
    nome_final = nome_do_instalador(args.rc)
    for antigo in os.listdir(destino_pasta):  # nunca deixar instalador/hash de builds anteriores misturados
        if antigo.startswith("PrintRoute-Setup-") or antigo == "SHA256SUMS.txt":
            os.remove(os.path.join(destino_pasta, antigo))
    cmd = [
        iscc,
        f"/DMyAppVersion={build_exe.__version__}",
        f"/DMyAppExe={exe_bruto}",
        f"/DMyGhostXpsDir={pasta_ghostxps}",
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
