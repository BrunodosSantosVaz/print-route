"""Regras do PR (.github/scripts/pr-regras.sh): nome de branch e destino corretos.
Só os cenários que não dependem da CLI do GitHub (gh)."""
import os
import subprocess
import unittest

import _caminho
from _bash import BASH, USAVEL

SCRIPT = os.path.join(_caminho.RAIZ, ".github", "scripts", "pr-regras.sh").replace("\\", "/")


@unittest.skipUnless(USAVEL, "bash/git utilizáveis não encontrados (ou Windows)")
class RegrasDoPR(unittest.TestCase):
    def rodar(self, head, base, titulo="", corpo=""):
        env = {**os.environ, "HEAD_REF": head, "BASE_REF": base, "PR_TITLE": titulo, "PR_BODY": corpo,
               "PR_NUMBER": "", "BRANCH_DEVELOP": "develop", "BRANCH_MAIN": "main"}
        return subprocess.run([BASH, SCRIPT], env=env, capture_output=True, text=True, cwd=_caminho.RAIZ)

    def test_release_para_a_main_passa(self):
        self.assertEqual(self.rodar("release/0.2.0", "main").returncode, 0)

    def test_release_para_a_develop_reprova(self):
        self.assertNotEqual(self.rodar("release/0.2.0", "develop").returncode, 0)

    def test_feature_para_a_main_reprova(self):
        self.assertNotEqual(self.rodar("feature/12-algo", "main", "x", "Refs #12").returncode, 0)

    def test_branch_fora_do_padrao_reprova(self):
        resultado = self.rodar("minha-branch", "develop")
        self.assertNotEqual(resultado.returncode, 0)
        self.assertIn("fora do padrao", resultado.stdout)

    def test_dependabot_para_a_develop_passa_sem_issue(self):
        resultado = self.rodar("dependabot/github_actions/develop/actions/checkout-7", "develop", "chore(deps): Bump actions/checkout")
        self.assertEqual(resultado.returncode, 0, resultado.stdout + resultado.stderr)

    def test_dependabot_para_a_main_reprova(self):
        self.assertNotEqual(self.rodar("dependabot/pip/x", "main").returncode, 0)


if __name__ == "__main__":
    unittest.main()
