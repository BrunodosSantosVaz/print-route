"""Gera o executável Windows do PrintRoute.

    python packaging/windows/build_exe.py                    # build-local/ (ignorada pelo git)
    python packaging/windows/build_exe.py --saida PASTA      # outra pasta
    python packaging/windows/build_exe.py --rc 2 --saida rc  # release candidata: PrintRoute-v<versão>-rc.2-...

Os executáveis oficiais (candidatas e produção) são gerados pelo CI (workflow "Build release
candidata") e ficam só nas Releases do GitHub, não à mão.

Requer Python 3.10+ (com Tkinter) e PyInstaller (`pip install -r requirements-build.txt`).
Resultado, na pasta de saída:
    PrintRoute-v<versão>[-rc.N]-windows-x64.exe
    SHA256SUMS.txt          (hash para conferir o download)
A versão vem do arquivo de versão (src/printroute/version.py) e é a mesma dentro do .exe em candidata ou
final: o sufixo -rc.N só aparece no nome do arquivo, para que o binário aprovado em homologação seja
exatamente o que vai para produção. Arquivos temporários do PyInstaller ficam fora do repositório.
"""
import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # packaging/windows/ -> raiz
SRC = os.path.join(RAIZ, "src")
sys.path.insert(0, SRC)
from printroute.version import __version__  # noqa: E402

NOME = "PrintRoute"
DESCRICAO = "PrintRoute: impressora virtual que reencaminha a impressão para outra(s) impressora(s)"
COPYRIGHT = "AGPL-3.0-or-later"


def arquivo_versao_windows(pasta):
    """Metadados que aparecem em Propriedades > Detalhes do .exe."""
    partes = (__version__.split(".") + ["0", "0", "0"])[:3]
    tupla = ", ".join(partes + ["0"])
    texto = f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers=({tupla}), prodvers=({tupla}), mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('041604B0', [
      StringStruct('FileDescription', '{DESCRICAO}'),
      StringStruct('FileVersion', '{__version__}'),
      StringStruct('InternalName', '{NOME}'),
      StringStruct('LegalCopyright', '{COPYRIGHT}'),
      StringStruct('OriginalFilename', '{NOME}.exe'),
      StringStruct('ProductName', 'PrintRoute'),
      StringStruct('ProductVersion', '{__version__}')])]),
    VarFileInfo([VarStruct('Translation', [1046, 1200])])
  ])
"""
    caminho = os.path.join(pasta, "version_info.txt")
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(texto)
    return caminho


def nome_do_arquivo(rc=None):
    """Nome do .exe: PrintRoute-v0.1.0-windows-x64.exe (produção) ou PrintRoute-v0.1.0-rc.1-windows-x64.exe."""
    sufixo = f"-rc.{int(rc)}" if rc else ""
    return f"{NOME}-v{__version__}{sufixo}-windows-x64.exe"


def sha256(caminho):
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1024 * 1024), b""):
            h.update(bloco)
    return h.hexdigest()


def compilar(destino_exe):
    """Roda o PyInstaller e copia o resultado para `destino_exe` (caminho completo,
    com nome). Reaproveitado por build_installer.py (tarefa #11), que precisa do .exe
    puro (sem o sufixo -rc.N/versão do nome público) para embutir no instalador."""
    with tempfile.TemporaryDirectory(prefix="printroute-build-") as tmp:
        cmd = [
            sys.executable, "-m", "PyInstaller", "--onefile", "--windowed", "--clean", "--noconfirm",
            "--name", NOME, "--version-file", arquivo_versao_windows(tmp),
            "--distpath", os.path.join(tmp, "dist"), "--workpath", os.path.join(tmp, "work"), "--specpath", tmp,
            "--paths", SRC, os.path.join(SRC, "printroute", "__main__.py"),
        ]
        print(" ".join(cmd))
        subprocess.run(cmd, check=True, cwd=SRC)
        gerado = os.path.join(tmp, "dist", NOME + ".exe")
        os.makedirs(os.path.dirname(destino_exe), exist_ok=True)
        shutil.copyfile(gerado, destino_exe)


def main():
    parser = argparse.ArgumentParser(description="Compila o PrintRoute e guarda o .exe com o hash SHA-256.")
    parser.add_argument("--saida", help="pasta de destino (padrão: build-local/)")
    parser.add_argument("--rc", type=int, help="número da release candidata (vira -rc.N no nome do arquivo)")
    args = parser.parse_args()
    destino_pasta = os.path.abspath(args.saida) if args.saida else os.path.join(RAIZ, "build-local")
    nome_final = nome_do_arquivo(args.rc)
    os.makedirs(destino_pasta, exist_ok=True)
    for antigo in os.listdir(destino_pasta):  # nunca deixar .exe/hash de builds anteriores misturados
        if antigo.endswith(".exe") or antigo == "SHA256SUMS.txt":
            os.remove(os.path.join(destino_pasta, antigo))
    final = os.path.join(destino_pasta, nome_final)
    compilar(final)
    with open(os.path.join(destino_pasta, "SHA256SUMS.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write(f"{sha256(final)}  {nome_final}\n")
    print(f"\nOK: {os.path.relpath(final, RAIZ)}  ({os.path.getsize(final) / 1e6:.1f} MB)")
    print(f"SHA-256: {sha256(final)}")


if __name__ == "__main__":
    main()
