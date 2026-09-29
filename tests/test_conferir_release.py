"""Portão de publicação (.github/scripts/conferir-release.sh): só publica versão com candidata testada
e código idêntico. Usa um repositório git temporário."""
import os
import shutil
import subprocess
import tempfile
import unittest

import _caminho
from _bash import BASH, USAVEL

SCRIPT = os.path.join(_caminho.RAIZ, ".github", "scripts", "conferir-release.sh")


@unittest.skipUnless(USAVEL, "bash/git utilizáveis não encontrados (ou Windows)")
class PortaoDeRelease(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.pasta, ignore_errors=True)
        os.makedirs(os.path.join(self.pasta, "src", "printroute"))
        os.makedirs(os.path.join(self.pasta, "packaging", "windows"))
        self.escrever("src/printroute/version.py", '__version__ = "0.2.0"\n')
        self.escrever("packaging/windows/build_exe.py", "# build\n")
        self.escrever("requirements-build.txt", "pyinstaller\n")
        self.escrever("CHANGELOG.md", "# Changelog\n\n## [0.2.0] - 2026-10-01\n\n- algo\n")
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.name", "t")
        self.git("config", "user.email", "t@t")
        self.git("config", "core.autocrlf", "false")
        self.git("add", ".")
        self.git("commit", "-q", "-m", "base")

    def escrever(self, caminho, texto):
        completo = os.path.join(self.pasta, caminho)
        with open(completo, "w", encoding="utf-8", newline="\n") as f:
            f.write(texto)

    def git(self, *args):
        subprocess.run(["git", *args], cwd=self.pasta, check=True, capture_output=True)

    def conferir(self):
        env = {**os.environ, "GITHUB_OUTPUT": os.path.join(self.pasta, "saida.txt")}
        return subprocess.run([BASH, SCRIPT.replace("\\", "/")], cwd=self.pasta, env=env, capture_output=True, text=True)

    def test_sem_candidata_reprova(self):
        r = self.conferir()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("Nao existe release candidata", r.stdout)

    def test_com_candidata_e_codigo_igual_passa(self):
        self.git("tag", "v0.2.0-rc.1")
        r = self.conferir()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        with open(os.path.join(self.pasta, "saida.txt"), encoding="utf-8") as f:
            self.assertIn("rc_tag=v0.2.0-rc.1", f.read())

    def test_usa_a_ultima_candidata(self):
        for tag in ("v0.2.0-rc.1", "v0.2.0-rc.2", "v0.2.0-rc.10"):
            self.git("tag", tag)
        r = self.conferir()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        with open(os.path.join(self.pasta, "saida.txt"), encoding="utf-8") as f:
            self.assertIn("rc_tag=v0.2.0-rc.10", f.read())  # ordem de versão, não alfabética

    def test_codigo_alterado_depois_da_candidata_reprova(self):
        self.git("tag", "v0.2.0-rc.1")
        self.escrever("src/printroute/__main__.py", "print('v2')\n")
        self.git("add", ".")
        self.git("commit", "-q", "-m", "mudou depois da rc")
        r = self.conferir()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("O codigo mudou depois da candidata", r.stdout)

    def test_compilador_alterado_depois_da_candidata_reprova(self):
        self.git("tag", "v0.2.0-rc.1")
        self.escrever("packaging/windows/build_exe.py", "# build alterado\n")
        self.git("commit", "-q", "-am", "mudou o compilador depois da rc")
        r = self.conferir()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("O codigo mudou depois da candidata", r.stdout)

    def test_mudanca_fora_do_codigo_nao_invalida_a_candidata(self):
        self.git("tag", "v0.2.0-rc.1")
        self.escrever("README.md", "docs\n")
        self.git("add", ".")
        self.git("commit", "-q", "-m", "docs")
        self.assertEqual(self.conferir().returncode, 0)

    def test_candidata_de_outra_versao_nao_serve(self):
        self.git("tag", "v0.1.0-rc.1")
        self.assertNotEqual(self.conferir().returncode, 0)

    def test_changelog_sem_a_versao_reprova(self):
        self.git("tag", "v0.2.0-rc.1")
        self.escrever("CHANGELOG.md", "# Changelog\n\n## [0.1.0] - 2026-09-21\n")
        r = self.conferir()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("CHANGELOG.md sem a secao", r.stdout)


if __name__ == "__main__":
    unittest.main()
