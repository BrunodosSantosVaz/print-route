"""Leitura das "Tarefas previstas" do corpo de um épico (.github/scripts/tarefas-do-epico.sh)."""
import os
import subprocess
import unittest

import _caminho
from _bash import BASH, USAVEL


SCRIPT = os.path.join(_caminho.RAIZ, ".github", "scripts", "tarefas-do-epico.sh").replace("\\", "/")


@unittest.skipUnless(USAVEL, "bash/git utilizáveis não encontrados (ou Windows)")
class TarefasDoEpico(unittest.TestCase):
    def ler(self, corpo):
        r = subprocess.run([BASH, SCRIPT], input=corpo.encode("utf-8"), capture_output=True, cwd=_caminho.RAIZ)
        self.assertEqual(r.returncode, 0, r.stderr.decode("utf-8", "replace"))
        return r.stdout.decode("utf-8").splitlines()

    def test_le_checklist(self):
        corpo = "### Problema\nx\n\n### Tarefas previstas\n- [ ] Primeira\n- [x] Segunda tarefa\n\n### Riscos\n- [ ] nao e tarefa\n"
        self.assertEqual(self.ler(corpo), ["Primeira", "Segunda tarefa"])

    def test_aceita_lista_simples_e_numerada(self):
        corpo = "### Tarefas previstas\n- A\n* B\n1. C\n2) ignorada\n"
        self.assertEqual(self.ler(corpo), ["A", "B", "C"])

    def test_ignora_itens_vazios_e_outras_secoes(self):
        corpo = "### Tarefas previstas\n- [ ] \n- [ ] Real\n### Escopo\n- [ ] fora\n"
        self.assertEqual(self.ler(corpo), ["Real"])

    def test_sem_secao_ou_sem_itens_nao_devolve_nada(self):
        self.assertEqual(self.ler("### Problema\ntexto\n"), [])
        self.assertEqual(self.ler("### Tarefas previstas\n\n_No response_\n"), [])

    def test_crlf_do_github_e_acentos(self):
        corpo = "### Tarefas previstas\r\n- [ ] Abrir o seletor de impressora\r\n- [ ] Corrigir\r\n"
        self.assertEqual(self.ler(corpo), ["Abrir o seletor de impressora", "Corrigir"])

    def test_nome_da_secao_exato(self):
        self.assertEqual(self.ler("### Tarefas previstas (extra)\n- [ ] x\n"), [])


if __name__ == "__main__":
    unittest.main()
