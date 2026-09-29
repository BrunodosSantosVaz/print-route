"""slug.sh: nome de branch a partir do título (deve casar com ^feature/[0-9]+-[a-z0-9-]+$)."""
import subprocess
import unittest

import _caminho
from _bash import BASH, posix, USAVEL

SCRIPT = posix(_caminho.RAIZ + "/.github/scripts/slug.sh")


@unittest.skipUnless(USAVEL, "bash/git utilizáveis não encontrados")
class Slug(unittest.TestCase):
    def slug(self, titulo):
        r = subprocess.run([BASH, SCRIPT, titulo], capture_output=True, cwd=_caminho.RAIZ)
        self.assertEqual(r.returncode, 0, r.stderr.decode("utf-8", "replace"))
        return r.stdout.decode("utf-8").strip()

    def test_tira_acentos_e_pontuacao(self):
        self.assertEqual(self.slug("Ação: Correção rápida!!!"), "acao-correcao-rapida")

    def test_limita_a_40_caracteres_sem_hifen_no_fim(self):
        s = self.slug("Reencaminhar a impressão para mais de uma impressora ao mesmo tempo")
        self.assertLessEqual(len(s), 40)
        self.assertFalse(s.endswith("-"))
        self.assertTrue(s.startswith("reencaminhar-a-impressao"))

    def test_vazio_ou_so_simbolos_vira_tarefa(self):
        self.assertEqual(self.slug("???"), "tarefa")
        self.assertEqual(self.slug(""), "tarefa")

    def test_resultado_sempre_valido_para_o_nome_da_branch(self):
        for titulo in ("Épico ÇÃO ñ", "  espaços   demais  ", "a/b\\c", "100% pronto (v2)"):
            with self.subTest(titulo=titulo):
                self.assertRegex(f"feature/12-{self.slug(titulo)}", r"^feature/[0-9]+-[a-z0-9-]+$")


if __name__ == "__main__":
    unittest.main()
