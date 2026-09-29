"""integrar-release.sh: trava do PR `sem-executavel`. A label "aprovado" num PR que não muda o
programa nunca cria versão, branch de release nem candidata. `gh` de mentira registra as chamadas."""
import json
import os
import shutil
import stat
import subprocess
import tempfile
import unittest

import _caminho
from _bash import BASH, USAVEL, posix

SCRIPT = posix(os.path.join(_caminho.RAIZ, ".github", "scripts", "integrar-release.sh"))

GH_FALSO = r'''#!/usr/bin/env bash
printf 'gh %s\n' "$(printf '%q ' "$@")" >> "$FIX/chamadas.log"
filtro=""
args=("$@")
for ((i = 0; i < ${#args[@]}; i++)); do [ "${args[i]}" = --jq ] && filtro="${args[i+1]}"; done
if [[ "$2" =~ ^repos/dono/repo/(issues|pulls)/([0-9]+)$ ]]; then json=$(cat "$FIX/${BASH_REMATCH[1]}-${BASH_REMATCH[2]}.json")
else json='[]'; fi
if [ -n "$filtro" ]; then jq -r "$filtro" <<<"$json"; else echo "$json"; fi
'''


@unittest.skipUnless(USAVEL and shutil.which("jq"), "bash/git/jq indisponíveis (roda no job scripts (Linux) do CI)")
class TravaSemExecutavel(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.fix = os.path.join(self.tmp, "fix")
        self.bin = os.path.join(self.tmp, "bin")
        os.makedirs(self.fix)
        os.makedirs(self.bin)
        gh = os.path.join(self.bin, "gh")
        with open(gh, "w", encoding="utf-8", newline="\n") as f:
            f.write(GH_FALSO)
        os.chmod(gh, os.stat(gh).st_mode | stat.S_IXUSR)

    def gravar(self, nome, dados):
        with open(os.path.join(self.fix, nome), "w", encoding="utf-8") as f:
            json.dump(dados, f)

    def pr(self, pr, issue, rotulos_pr=(), rotulos_issue=(), milestone=None):
        self.gravar(f"pulls-{pr}.json", {"head": {"ref": f"feature/{issue}-tarefa"}})
        self.gravar(f"issues-{pr}.json", {"labels": [{"name": n} for n in rotulos_pr]})
        self.gravar(f"issues-{issue}.json", {"labels": [{"name": n} for n in rotulos_issue],
                                             "milestone": {"title": milestone} if milestone else None})

    def rodar(self, pr):
        env = dict(os.environ, PATH=posix(self.bin) + os.pathsep + os.environ["PATH"], FIX=posix(self.fix),
                   GITHUB_REPOSITORY="dono/repo", PROJETO_EXECUCAO="11", PROJETO_BUGS="12", PR_NUMBER=str(pr),
                   AUTO="true", SIMULAR="false")
        r = subprocess.run([BASH, SCRIPT], env=env, capture_output=True, text=True, cwd=self.tmp)
        with open(os.path.join(self.fix, "chamadas.log"), encoding="utf-8") as f:
            return r, r.stdout + r.stderr, f.read()

    def test_issue_sem_executavel_com_aprovado_nao_integra(self):
        self.pr(50, 33, rotulos_pr=("aprovado",), rotulos_issue=("task", "sem-executavel"), milestone="v0.3.0")
        r, saida, chamadas = self.rodar(50)
        self.assertEqual(r.returncode, 0, saida)
        self.assertIn("PR #50 e sem-executavel", saida)
        self.assertNotIn("milestones", chamadas)  # nem chegou a procurar a versao

    def test_pr_com_a_label_sem_executavel_nao_integra(self):
        self.pr(51, 34, rotulos_pr=("aprovado", "sem-executavel"), rotulos_issue=("task",), milestone="v0.3.0")
        r, saida, chamadas = self.rodar(51)
        self.assertEqual(r.returncode, 0, saida)
        self.assertIn("PR #51 e sem-executavel", saida)
        self.assertNotIn("milestones", chamadas)

    def test_pr_que_muda_o_programa_segue_para_a_integracao(self):
        self.pr(52, 35, rotulos_pr=("aprovado",), rotulos_issue=("task",), milestone="v0.3.0")
        r, saida, chamadas = self.rodar(52)
        self.assertNotIn("sem-executavel", saida)
        self.assertIn("milestones", chamadas)  # passou da trava e foi procurar o milestone da versao


if __name__ == "__main__":
    unittest.main()
