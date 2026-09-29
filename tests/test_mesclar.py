"""mesclar.sh: merge uma a uma (--no-ff) de PRs/branches em uma branch de destino, com git de verdade
em repositórios temporários (um "origin" bare e um clone que faz o papel do runner)."""
import os
import shutil
import subprocess
import tempfile
import unittest

import _caminho
from _bash import BASH, GIT, posix, USAVEL

SCRIPT = posix(_caminho.RAIZ + "/.github/scripts/mesclar.sh")


@unittest.skipUnless(USAVEL, "bash/git utilizáveis não encontrados")
class Mesclar(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.origin = os.path.join(self.tmp, "origin.git")
        self.dono = os.path.join(self.tmp, "dono")
        self.git(self.tmp, "init", "-q", "--bare", "-b", "develop", self.origin)
        os.makedirs(self.dono)
        self.git(self.dono, "init", "-q", "-b", "develop")
        for k, v in (("user.name", "t"), ("user.email", "t@t"), ("core.autocrlf", "false")):
            self.git(self.dono, "config", k, v)
        self.git(self.dono, "remote", "add", "origin", self.origin)
        self.escrever(self.dono, "README.md", "linha 1\nlinha 2\n")
        self.git(self.dono, "add", ".")
        self.git(self.dono, "commit", "-q", "-m", "base")
        self.git(self.dono, "push", "-q", "origin", "develop")

    # utilitários ---------------------------------------------------------
    def git(self, pasta, *args):
        r = subprocess.run([GIT, *args], cwd=pasta, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, f"git {args}: {r.stderr}")
        return r.stdout.strip()

    def escrever(self, pasta, nome, texto):
        with open(os.path.join(pasta, nome), "w", encoding="utf-8", newline="\n") as f:
            f.write(texto)

    def pr(self, numero, arquivo, texto):
        """Cria o commit numa branch temporária e publica como refs/pull/<n>/head."""
        self.git(self.dono, "checkout", "-q", "-B", f"tmp{numero}", "develop")
        self.escrever(self.dono, arquivo, texto)
        self.git(self.dono, "add", ".")
        self.git(self.dono, "commit", "-q", "-m", f"pr {numero}")
        self.git(self.dono, "push", "-q", "origin", f"tmp{numero}:refs/pull/{numero}/head")
        self.git(self.dono, "checkout", "-q", "develop")

    def runner(self):
        pasta = os.path.join(self.tmp, "runner")
        shutil.rmtree(pasta, ignore_errors=True)
        self.git(self.tmp, "clone", "-q", self.origin, pasta)
        for k, v in (("user.name", "t"), ("user.email", "t@t"), ("core.autocrlf", "false")):
            self.git(pasta, "config", k, v)
        return pasta

    def mesclar(self, pasta, destino, base, *itens):
        return subprocess.run([BASH, SCRIPT, destino, base, *itens], cwd=pasta, capture_output=True, text=True)

    # testes ----------------------------------------------------------------
    def test_mescla_uma_por_uma_criando_o_destino_a_partir_da_base(self):
        self.pr(1, "a.txt", "a\n")
        self.pr(2, "b.txt", "b\n")
        pasta = self.runner()
        r = self.mesclar(pasta, "release/0.2.0", "develop", "PR#1=refs/pull/1/head", "PR#2=refs/pull/2/head")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.split(), ["MESCLADO", "PR#1", "MESCLADO", "PR#2"])
        self.assertEqual(self.git(pasta, "branch", "--show-current"), "release/0.2.0")
        self.assertTrue(os.path.exists(os.path.join(pasta, "a.txt")) and os.path.exists(os.path.join(pasta, "b.txt")))
        merges = self.git(pasta, "log", "--merges", "--format=%s").splitlines()
        self.assertEqual(merges, ["Merge PR#2", "Merge PR#1"])  # um commit de merge por item, na ordem

    def test_conflito_aborta_sem_sujar_a_branch(self):
        self.pr(1, "README.md", "linha 1\nmudou pelo PR 1\n")
        self.pr(2, "README.md", "linha 1\nmudou pelo PR 2\n")
        pasta = self.runner()
        r = self.mesclar(pasta, "release/0.2.0", "develop", "PR#1=refs/pull/1/head", "PR#2=refs/pull/2/head")
        self.assertEqual(r.returncode, 3)
        self.assertEqual(r.stdout.split(), ["MESCLADO", "PR#1", "CONFLITO", "PR#2"])
        self.assertEqual(self.git(pasta, "status", "--porcelain"), "")           # sem merge pela metade
        self.assertEqual(self.git(pasta, "log", "--merges", "--format=%s"), "Merge PR#1")

    def test_reexecutar_nao_repete_o_que_ja_entrou(self):
        self.pr(1, "a.txt", "a\n")
        pasta = self.runner()
        self.assertEqual(self.mesclar(pasta, "release/0.2.0", "develop", "PR#1=refs/pull/1/head").returncode, 0)
        self.git(pasta, "push", "-q", "origin", "release/0.2.0")
        self.pr(2, "b.txt", "b\n")                                               # novo PR (correção) depois
        pasta = self.runner()
        r = self.mesclar(pasta, "release/0.2.0", "develop", "PR#1=refs/pull/1/head", "PR#2=refs/pull/2/head")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.split(), ["JA_INCLUIDO", "PR#1", "MESCLADO", "PR#2"])

    def test_mescla_release_na_develop(self):
        self.pr(1, "a.txt", "a\n")
        pasta = self.runner()
        self.mesclar(pasta, "release/0.2.0", "develop", "PR#1=refs/pull/1/head")
        self.git(pasta, "push", "-q", "origin", "release/0.2.0")
        pasta = self.runner()
        r = self.mesclar(pasta, "develop", "develop", "release/0.2.0=refs/heads/release/0.2.0")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.split(), ["MESCLADO", "release/0.2.0"])
        self.assertTrue(os.path.exists(os.path.join(pasta, "a.txt")))


if __name__ == "__main__":
    unittest.main()
