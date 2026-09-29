"""criar-branches.sh: tarefas com milestone ganham branch; sem milestone só as `sem-executavel` que
estão numa Sprint (sprint sem versão). `gh` e `projeto.sh` de mentira registram as chamadas."""
import json
import os
import shutil
import stat
import subprocess
import tempfile
import unittest

import _caminho
from _bash import BASH, USAVEL, posix

SCRIPTS = os.path.join(_caminho.RAIZ, ".github", "scripts")

GH_FALSO = r'''#!/usr/bin/env bash
printf 'gh %s\n' "$(printf '%q ' "$@")" >> "$FIX/chamadas.log"
filtro=""
args=("$@")
for ((i = 0; i < ${#args[@]}; i++)); do [ "${args[i]}" = --jq ] && filtro="${args[i+1]}"; done
if [[ "$2" =~ ^repos/dono/repo/issues/([0-9]+)$ ]]; then json=$(cat "$FIX/issue-${BASH_REMATCH[1]}.json")
elif [[ "$*" == *"git/ref/heads/develop"* ]]; then json='{"object":{"sha":"abc"}}'
elif [[ "$*" == *"git/ref/heads/"* ]]; then exit 1   # branch ainda nao existe
else json='{}'; fi
if [ -n "$filtro" ]; then jq -r "$filtro" <<<"$json"; else echo "$json"; fi
'''

PROJETO_FALSO = r'''#!/usr/bin/env bash
printf 'projeto %s\n' "$*" >> "$FIX/chamadas.log"
case "$1" in
  cartoes) [ "$2" = 11 ] && [ "$3" = "A fazer" ] && cat "$FIX/afazer" ;;
  sprint-de) cat "$FIX/sprint-$3" 2>/dev/null || true ;;
esac
exit 0
'''


@unittest.skipUnless(USAVEL and shutil.which("jq"), "bash/git/jq indisponíveis (roda no job scripts (Linux) do CI)")
class CriarBranches(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.fix = os.path.join(self.tmp, "fix")
        self.bin = os.path.join(self.tmp, "bin")
        self.scripts = os.path.join(self.tmp, "scripts")
        for p in (self.fix, self.bin, self.scripts):
            os.makedirs(p)
        for nome in ("criar-branches.sh", "slug.sh"):
            shutil.copy(os.path.join(SCRIPTS, nome), self.scripts)
        self.exec_(os.path.join(self.bin, "gh"), GH_FALSO)
        self.exec_(os.path.join(self.scripts, "projeto.sh"), PROJETO_FALSO)

    def exec_(self, caminho, texto):
        with open(caminho, "w", encoding="utf-8", newline="\n") as f:
            f.write(texto)
        os.chmod(caminho, os.stat(caminho).st_mode | stat.S_IXUSR)

    def gravar(self, nome, texto):
        with open(os.path.join(self.fix, nome), "w", encoding="utf-8", newline="\n") as f:
            f.write(texto)

    def tarefa(self, n, titulo, milestone=None, sem_executavel=False, sprint=None):
        labels = [{"name": "task"}] + ([{"name": "sem-executavel"}] if sem_executavel else [])
        self.gravar(f"issue-{n}.json", json.dumps({"state": "open", "title": titulo, "labels": labels,
                                                   "milestone": {"title": milestone} if milestone else None}))
        if sprint:
            self.gravar(f"sprint-{n}", sprint + "\n")

    def rodar(self, **extra):
        env = dict(os.environ, PATH=posix(self.bin) + os.pathsep + os.environ["PATH"], FIX=posix(self.fix),
                   GITHUB_REPOSITORY="dono/repo", PROJETO_EXECUCAO="11", PROJETO_BUGS="12", SIMULAR="false", **extra)
        r = subprocess.run([BASH, posix(os.path.join(self.scripts, "criar-branches.sh"))], env=env,
                           capture_output=True, text=True)
        return r, r.stdout + r.stderr

    def branches(self):
        with open(os.path.join(self.fix, "chamadas.log"), encoding="utf-8") as f:
            return [linha.split("ref=refs/heads/")[1].split()[0] for linha in f if "ref=refs/heads/" in linha]

    def test_milestone_e_sem_executavel_na_sprint_ganham_branch(self):
        self.tarefa(40, "Layout novo", milestone="v0.3.0")
        self.tarefa(41, "Docs da esteira", sem_executavel=True, sprint="Sprint 1")
        self.gravar("afazer", "40\n41\n")
        r, saida = self.rodar()
        self.assertEqual(r.returncode, 0, saida)
        self.assertEqual(self.branches(), ["feature/40-layout-novo", "feature/41-docs-da-esteira"])
        self.assertIn("#41 sem-executavel na Sprint 1 (sem versao).", saida)

    def test_sem_milestone_fora_de_sprint_ou_tarefa_comum_continua_backlog(self):
        self.tarefa(42, "Ideia solta", sem_executavel=True)
        self.tarefa(43, "Tarefa comum", sprint="Sprint 1")
        self.gravar("afazer", "42\n43\n")
        r, saida = self.rodar()
        self.assertEqual(r.returncode, 0, saida)
        self.assertEqual(self.branches(), [])
        self.assertIn("#42 sem milestone (backlog): ignorada.", saida)
        self.assertIn("#43 sem milestone (backlog): ignorada.", saida)

    def test_filtro_de_sprint(self):
        self.tarefa(44, "Docs A", sem_executavel=True, sprint="Sprint 1")
        self.tarefa(45, "Docs B", sem_executavel=True, sprint="Sprint 2")
        self.gravar("afazer", "44\n45\n")
        r, saida = self.rodar(SPRINT="Sprint 2")
        self.assertEqual(r.returncode, 0, saida)
        self.assertEqual(self.branches(), ["feature/45-docs-b"])

    def test_filtro_de_versao_nao_afeta_as_sem_executavel_da_sprint(self):
        self.tarefa(46, "Layout", milestone="v0.3.0")
        self.tarefa(47, "Outra versao", milestone="v0.4.0")
        self.tarefa(48, "Docs", sem_executavel=True, sprint="Sprint 1")
        self.gravar("afazer", "46\n47\n48\n")
        r, saida = self.rodar(VERSAO="v0.3.0")
        self.assertEqual(r.returncode, 0, saida)
        self.assertEqual(self.branches(), ["feature/46-layout", "feature/48-docs"])


if __name__ == "__main__":
    unittest.main()
