"""Resposta do campo "Muda o programa?" do formulário de épico (.github/scripts/muda-programa.sh)."""
import os
import subprocess
import unittest

import _caminho
from _bash import BASH, USAVEL

SCRIPT = os.path.join(_caminho.RAIZ, ".github", "scripts", "muda-programa.sh").replace("\\", "/")
FORMULARIO = os.path.join(_caminho.RAIZ, ".github", "ISSUE_TEMPLATE", "epico.yml")


@unittest.skipUnless(USAVEL, "bash/git utilizáveis não encontrados (ou Windows)")
class MudaPrograma(unittest.TestCase):
    def ler(self, corpo):
        r = subprocess.run([BASH, SCRIPT], input=corpo.encode("utf-8"), capture_output=True, cwd=_caminho.RAIZ)
        self.assertEqual(r.returncode, 0, r.stderr.decode("utf-8", "replace"))
        return r.stdout.decode("utf-8").strip()

    def corpo(self, resposta):
        return f"### Problema / oportunidade\nx\n\n### Muda o programa?\n\n{resposta}\n\n### Escopo (dentro e fora)\nNão sei\n"

    def test_nao(self):
        self.assertEqual(self.ler(self.corpo("Não: documentação, testes, esteira ou compilador (sprint sem versão)")), "nao")

    def test_sim(self):
        self.assertEqual(self.ler(self.corpo("Sim: mexe em src/ ou nas dependências de build (gera versão)")), "sim")

    def test_sem_campo_ou_sem_resposta_e_vazio(self):
        self.assertEqual(self.ler("### Problema\nx\n\n### Tarefas previstas\n- [ ] a\n"), "")
        self.assertEqual(self.ler(self.corpo("_No response_")), "")

    def test_nao_le_outras_secoes(self):
        self.assertEqual(self.ler("### Escopo\nNão: isto é outra seção\n"), "")

    def test_crlf_do_github(self):
        self.assertEqual(self.ler(self.corpo("Não: docs").replace("\n", "\r\n")), "nao")

    def test_corpo_grande_nao_quebra_o_pipe(self):
        # regressao: com "exit" no awk, um corpo maior que o buffer do pipe fazia o tr morrer com
        # SIGPIPE (exit 141) e o Kanban falhava sem aplicar a label (epico #45)
        corpo = self.corpo("Não: docs") + ("linha de detalhamento do épico " * 8 + "\n") * 1000
        self.assertGreater(len(corpo.encode("utf-8")), 200_000)
        self.assertEqual(self.ler(corpo), "nao")  # ler() confere o codigo de saida 0

    def test_primeira_resposta_vale(self):
        self.assertEqual(self.ler(self.corpo("Não: docs\nSim: outra linha")), "nao")

    def test_opcoes_do_formulario_sao_as_que_o_leitor_entende(self):
        with open(FORMULARIO, encoding="utf-8") as f:
            texto = f.read()
        self.assertIn("label: Muda o programa?", texto)
        opcoes = [linha.strip()[3:-1] for linha in texto.splitlines() if linha.strip().startswith('- "')]
        self.assertEqual([self.ler(self.corpo(o)) for o in opcoes], ["sim", "nao"])


if __name__ == "__main__":
    unittest.main()
