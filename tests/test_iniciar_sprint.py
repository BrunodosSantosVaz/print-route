"""iniciar-sprint.sh: sprint x versão. Épico que muda o programa usa o milestone da versão;
épico `sem-executavel` roda sem versão e sem milestone. `gh` e `projeto.sh` de mentira registram
as chamadas."""
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
filtro="" consulta=""
args=("$@")
for ((i = 0; i < ${#args[@]}; i++)); do
  case "${args[i]}" in --jq) filtro="${args[i+1]}" ;; query=*) consulta="${args[i]}" ;; esac
done
if [ "$1" = issue ] && [ "$2" = create ]; then
  n=$(( $(cat "$FIX/proximo" 2>/dev/null || echo 100) + 1 )); echo "$n" > "$FIX/proximo"
  echo "https://github.com/dono/repo/issues/$n"; exit 0
fi
if [[ "$*" == *"-X POST"*milestones* ]]; then json='{"number":7}'
elif [[ "$2" == repos/dono/repo/milestones* ]]; then json='[]'
elif [[ "$2" =~ ^repos/dono/repo/issues/([0-9]+)$ ]]; then
  f="$FIX/issue-${BASH_REMATCH[1]}.json"
  if [ -f "$f" ]; then json=$(cat "$f"); else json='{"node_id":"NOVA","title":"","labels":[],"body":""}'; fi
elif [[ "$consulta" == *subIssues* ]]; then json='{"data":{"repository":{"issue":{"subIssues":{"nodes":[]}}}}}'
else json='{}'; fi
if [ -n "$filtro" ]; then jq -r "$filtro" <<<"$json"; else echo "$json"; fi
'''

PROJETO_FALSO = r'''#!/usr/bin/env bash
printf 'projeto %s\n' "$*" >> "$FIX/chamadas.log"
case "$1" in
  cartoes) [ "$3" = "Próxima sprint" ] && cat "$FIX/proxima" ;;
  sprint-atual) cat "$FIX/sprint" 2>/dev/null || true ;;
esac
exit 0
'''


def corpo(*tarefas):
    return "### Problema\nx\n\n### Tarefas previstas\n" + "".join(f"- [ ] {t}\n" for t in tarefas)


@unittest.skipUnless(USAVEL and shutil.which("jq"), "bash/git/jq indisponíveis (roda no job scripts (Linux) do CI)")
class IniciarSprint(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.fix = os.path.join(self.tmp, "fix")
        self.bin = os.path.join(self.tmp, "bin")
        self.scripts = os.path.join(self.tmp, "scripts")
        for p in (self.fix, self.bin, self.scripts):
            os.makedirs(p)
        for nome in ("iniciar-sprint.sh", "tarefas-do-epico.sh"):
            shutil.copy(os.path.join(SCRIPTS, nome), self.scripts)
        self.exec_(os.path.join(self.bin, "gh"), GH_FALSO)
        self.exec_(os.path.join(self.scripts, "projeto.sh"), PROJETO_FALSO)
        self.gravar("sprint", "Sprint 4\n")

    def exec_(self, caminho, texto):
        with open(caminho, "w", encoding="utf-8", newline="\n") as f:
            f.write(texto)
        os.chmod(caminho, os.stat(caminho).st_mode | stat.S_IXUSR)

    def gravar(self, nome, texto):
        with open(os.path.join(self.fix, nome), "w", encoding="utf-8", newline="\n") as f:
            f.write(texto)

    def epico(self, n, titulo, tarefas, sem_executavel=False):
        labels = [{"name": "epic"}] + ([{"name": "sem-executavel"}] if sem_executavel else [])
        self.gravar(f"issue-{n}.json", json.dumps({"node_id": f"E{n}", "title": titulo, "labels": labels,
                                                   "body": corpo(*tarefas)}))

    def proxima(self, *numeros):
        self.gravar("proxima", "".join(f"{n}\n" for n in numeros))

    def rodar(self, versao="", simular=False, **extra):
        env = dict(os.environ, PATH=posix(self.bin) + os.pathsep + os.environ["PATH"], FIX=posix(self.fix),
                   GITHUB_REPOSITORY="dono/repo", PROJETO_PLANEJAMENTO="10", PROJETO_EXECUCAO="11",
                   VERSAO=versao, SIMULAR="true" if simular else "false", **extra)
        r = subprocess.run([BASH, posix(os.path.join(self.scripts, "iniciar-sprint.sh"))], env=env,
                           capture_output=True, text=True)
        return r, r.stdout + r.stderr

    def chamadas(self):
        caminho = os.path.join(self.fix, "chamadas.log")
        if not os.path.exists(caminho):
            return []
        with open(caminho, encoding="utf-8") as f:
            return f.read().splitlines()

    def criadas(self):
        return [c for c in self.chamadas() if c.startswith("gh issue create")]

    def criou_milestone(self):
        return any("-X POST" in c and "milestones" in c for c in self.chamadas())

    def test_so_sem_executavel_roda_sem_versao_e_sem_milestone(self):
        self.epico(21, "Documentação", ["Compilador", "Docs"], sem_executavel=True)
        self.proxima(21)
        r, saida = self.rodar()
        self.assertEqual(r.returncode, 0, saida)
        self.assertFalse(self.criou_milestone())
        self.assertEqual(len(self.criadas()), 2)
        for c in self.criadas():
            self.assertIn("sem-executavel", c)
            self.assertNotIn("--milestone", c)
        self.assertIn("projeto sprint 11 101 Sprint 4", self.chamadas())
        self.assertIn("projeto sprint 10 21 Sprint 4", self.chamadas())
        self.assertIn("projeto mover 10 21 Em desenvolvimento Próxima sprint", self.chamadas())
        self.assertIn("sem versao: nada sera compilado", saida)

    def test_epico_que_muda_o_programa_sem_versao_recusa_sem_criar_nada(self):
        self.epico(4, "Selecionar impressora", ["Layout 400"])
        self.proxima(4)
        r, saida = self.rodar()
        self.assertEqual(r.returncode, 1, saida)
        self.assertIn("#4 mudam o programa", saida)
        self.assertEqual(self.criadas(), [])
        self.assertFalse(self.criou_milestone())
        self.assertFalse(any(c.startswith("projeto mover") for c in self.chamadas()))

    def test_sprint_mista_com_versao(self):
        self.epico(4, "Selecionar impressora", ["Layout 400"])
        self.epico(21, "Documentação", ["Compilador"], sem_executavel=True)
        self.proxima(4, 21)
        r, saida = self.rodar(versao="v0.3.0")
        self.assertEqual(r.returncode, 0, saida)
        self.assertTrue(self.criou_milestone())
        layout, compilador = self.criadas()
        self.assertIn("--milestone v0.3.0", layout)
        self.assertNotIn("sem-executavel", layout)
        self.assertIn("sem-executavel", compilador)
        self.assertNotIn("--milestone", compilador)

    def test_versao_informada_mas_todos_sem_executavel_nao_cria_milestone(self):
        self.epico(21, "Documentação", ["Compilador"], sem_executavel=True)
        self.proxima(21)
        r, saida = self.rodar(versao="v0.3.0")
        self.assertEqual(r.returncode, 0, saida)
        self.assertIn("a versao v0.3.0 foi ignorada", saida)
        self.assertFalse(self.criou_milestone())
        self.assertNotIn("--milestone", self.criadas()[0])

    def test_simulacao_nao_cria_nada(self):
        self.epico(21, "Documentação", ["Compilador"], sem_executavel=True)
        self.proxima(21)
        r, saida = self.rodar(simular=True)
        self.assertEqual(r.returncode, 0, saida)
        self.assertIn("[simulado] criar tarefa 'Compilador' (task, sem versao, sem-executavel", saida)
        self.assertEqual(self.criadas(), [])

    def test_sprint_indicada_e_sem_campo_sprint(self):
        self.epico(21, "Documentação", ["Compilador"], sem_executavel=True)
        self.proxima(21)
        self.rodar(SPRINT="Sprint 9")
        self.assertIn("projeto sprint 11 101 Sprint 9", self.chamadas())
        os.remove(os.path.join(self.fix, "sprint"))
        os.remove(os.path.join(self.fix, "chamadas.log"))
        self.epico(22, "Outro", ["Tarefa"], sem_executavel=True)
        self.proxima(22)
        r, saida = self.rodar()
        self.assertEqual(r.returncode, 0, saida)
        self.assertIn("Nenhuma Sprint atual", saida)
        self.assertFalse(any(c.startswith("projeto sprint ") for c in self.chamadas()))

    def test_versao_invalida(self):
        self.proxima(21)
        r, saida = self.rodar(versao="v0.2.0-nc")
        self.assertEqual(r.returncode, 1)
        self.assertIn("invalida", saida)


if __name__ == "__main__":
    unittest.main()
