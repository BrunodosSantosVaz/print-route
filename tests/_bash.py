"""Localiza um bash utilizável para os testes dos scripts (.github/scripts/*.sh)."""
import os
import shutil


def achar_bash():
    """No Windows o "bash" do PATH costuma ser o iniciador do WSL (System32/WindowsApps), que não
    entende caminhos C:/; nesse caso usa o Git Bash. Em Linux/macOS usa o bash do PATH."""
    candidatos = [shutil.which("bash"), r"C:\Program Files\Git\bin\bash.exe", r"C:\Program Files\Git\usr\bin\bash.exe"]
    for c in candidatos:
        if c and os.path.exists(c) and not any(x in c.lower() for x in ("system32", "windowsapps")):
            return c
    return None


BASH = achar_bash()
GIT = shutil.which("git")
# Os scripts do processo rodam no Linux das Actions (ubuntu-latest). No Windows (git/arquivos presos,
# python3 ausente no Git Bash) esses testes são pulados: o job "scripts (Linux)" do CI os executa.
USAVEL = bool(BASH and GIT) and os.name != "nt"


def posix(caminho):
    return caminho.replace("\\", "/")
