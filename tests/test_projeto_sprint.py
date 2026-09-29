"""projeto.sh sprint / sprint-atual / sprint-de: campo "Sprint" (Iteration) dos painéis, com `gh` de
mentira que devolve um painel com três sprints de 2 semanas e registra as mutações."""
import json
import os
import shutil
import stat
import subprocess
import tempfile
import unittest

import _caminho
from _bash import BASH, USAVEL, posix

SCRIPT = posix(_caminho.RAIZ + "/.github/scripts/projeto.sh")

PAINEL = {"data": {"repositoryOwner": {"projectV2": {"id": "PVT_1", "field": {"id": "CAMPO_SPRINT", "configuration": {
    "iterations": [
        {"id": "it1", "title": "Sprint 1", "startDate": "2026-09-21", "duration": 14},
        {"id": "it2", "title": "Sprint 2", "startDate": "2026-10-05", "duration": 14},
        {"id": "it3", "title": "Sprint 3", "startDate": "2026-10-19", "duration": 14},
    ]}}}}}}

# Responde conforme a consulta e aplica o --jq de verdade (jq), como o gh faria.
GH_FALSO = r'''#!/usr/bin/env bash
printf 'gh %s\n' "$(printf '%q ' "$@")" >> "$FIX/chamadas.log"  # uma chamada por linha
filtro="" consulta=""
args=("$@")
for ((i = 0; i < ${#args[@]}; i++)); do
  case "${args[i]}" in
    --jq) filtro="${args[i+1]}" ;;
    query=*) consulta="${args[i]}" ;;
  esac
done
if [[ "$1 $2" == "api repos/"* ]]; then json='{"node_id":"ISSUE_NODE"}'
elif [[ "$consulta" == *addProjectV2ItemById* ]]; then json='{"data":{"addProjectV2ItemById":{"item":{"id":"ITEM_1"}}}}'
elif [[ "$consulta" == *updateProjectV2ItemFieldValue* ]]; then json='{}'
elif [[ "$consulta" == *ProjectV2ItemFieldIterationValue* ]]; then json=$(cat "$FIX/valor.json")
else json=$(cat "$FIX/painel.json"); fi
if [ -n "$filtro" ]; then jq -r "$filtro" <<<"$json"; else echo "$json"; fi
'''


@unittest.skipUnless(USAVEL and shutil.which("jq"), "bash/git/jq indisponíveis (roda no job scripts (Linux) do CI)")
class Sprint(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.fix = os.path.join(self.tmp, "fix")
        bin_ = os.path.join(self.tmp, "bin")
        os.makedirs(self.fix)
        os.makedirs(bin_)
        gh = os.path.join(bin_, "gh")
        with open(gh, "w", encoding="utf-8", newline="\n") as f:
            f.write(GH_FALSO)
        os.chmod(gh, os.stat(gh).st_mode | stat.S_IXUSR)
        self.bin = bin_
        with open(os.path.join(self.fix, "painel.json"), "w", encoding="utf-8") as f:
            json.dump(PAINEL, f)
        self.valor({"data": {"node": {"fieldValueByName": {"title": "Sprint 2"}}}})

    def valor(self, dados):
        with open(os.path.join(self.fix, "valor.json"), "w", encoding="utf-8") as f:
            json.dump(dados, f)

    def rodar(self, *args, hoje="2026-09-27", **extra):
        env = dict(os.environ, PATH=posix(self.bin) + os.pathsep + os.environ["PATH"], FIX=posix(self.fix),
                   PROJETO_OWNER="dono", GITHUB_REPOSITORY="dono/repo", HOJE=hoje, **extra)
        return subprocess.run([BASH, SCRIPT, *args], env=env, capture_output=True, text=True)

    def chamadas(self):
        caminho = os.path.join(self.fix, "chamadas.log")
        if not os.path.exists(caminho):
            return []
        with open(caminho, encoding="utf-8") as f:
            return f.read().splitlines()

    def test_sprint_atual_pela_data(self):
        for hoje, esperado in (("2026-09-21", "Sprint 1"), ("2026-10-04", "Sprint 1"), ("2026-10-05", "Sprint 2"),
                               ("2026-10-20", "Sprint 3")):
            with self.subTest(hoje=hoje):
                r = self.rodar("sprint-atual", "11", hoje=hoje)
                self.assertEqual(r.returncode, 0, r.stderr)
                self.assertEqual(r.stdout.strip(), esperado)

    def test_fora_de_qualquer_sprint_imprime_vazio(self):
        r = self.rodar("sprint-atual", "11", hoje="2027-01-01")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), "")

    def test_poe_a_issue_na_sprint_atual(self):
        r = self.rodar("sprint", "11", "33")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("#33 no painel 11: Sprint 'Sprint 1'.", r.stdout)
        mutacao = [c for c in self.chamadas() if "updateProjectV2ItemFieldValue" in c]
        self.assertEqual(len(mutacao), 1)
        self.assertIn("t=it1", mutacao[0])
        self.assertIn("f=CAMPO_SPRINT", mutacao[0])

    def test_poe_a_issue_na_sprint_pelo_nome(self):
        r = self.rodar("sprint", "11", "33", "Sprint 3")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(any("t=it3" in c for c in self.chamadas() if "updateProjectV2ItemFieldValue" in c))

    def test_simulacao_nao_altera(self):
        r = self.rodar("sprint", "11", "33", DRY_RUN="1")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("[simulado] painel 11: #33 -> Sprint 'Sprint 1'", r.stdout)
        self.assertFalse(any("updateProjectV2ItemFieldValue" in c for c in self.chamadas()))

    def test_sprint_inexistente_falha(self):
        r = self.rodar("sprint", "11", "33", "Sprint 9")
        self.assertEqual(r.returncode, 1)
        self.assertIn("Sprint 'Sprint 9' nao encontrada", r.stderr)

    def test_sprint_de_uma_issue(self):
        r = self.rodar("sprint-de", "11", "33")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), "Sprint 2")
        self.valor({"data": {"node": {"fieldValueByName": None}}})
        self.assertEqual(self.rodar("sprint-de", "11", "33").stdout.strip(), "")


if __name__ == "__main__":
    unittest.main()
