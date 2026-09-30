"""Issues `sem-executavel` (docs, testes, CI): o critério "toca o executável" (toca-executavel.sh) e a
ação publicar-sem-executavel.sh (portão, avanço da main e finalização), com git de verdade e um `gh`
de mentira que registra as chamadas."""
import json
import os
import shutil
import stat
import subprocess
import tempfile
import unittest

import _caminho
from _bash import BASH, GIT, posix, USAVEL

SCRIPTS = _caminho.RAIZ + "/.github/scripts"
JQ = shutil.which("jq")

GH_FALSO = r'''#!/usr/bin/env bash
echo "gh $*" >> "$FIX/chamadas.log"
jqarg=""; args=("$@")
for ((i = 0; i < ${#args[@]}; i++)); do [ "${args[i]}" = --jq ] && jqarg="${args[i+1]}"; done
emitir() { if [ -n "$jqarg" ]; then jq -r "$jqarg" "$1"; else cat "$1"; fi; }
case "$*" in
  "api repos/o/r/commits/"*"/check-runs"*) emitir "$FIX/checks.json" ;;
  "api repos/o/r/issues?labels=sem-executavel"*) emitir "$FIX/issues.json" ;;
  "api repos/o/r/pulls?state=closed"*) emitir "$FIX/prs.json" ;;
esac
exit 0
'''

PROJETO_FALSO = r'''#!/usr/bin/env bash
echo "projeto $*" >> "$FIX/chamadas.log"
[ "$1" = cartoes ] || exit 0
f="$FIX/cartoes_$2_$3"
[ ! -f "$f" ] || cat "$f"
'''


def exec_(caminho, texto):
    with open(caminho, "w", encoding="utf-8", newline="\n") as f:
        f.write(texto)
    os.chmod(caminho, os.stat(caminho).st_mode | stat.S_IXUSR)


@unittest.skipUnless(USAVEL, "bash/git utilizáveis não encontrados (ou Windows)")
class TocaExecutavel(unittest.TestCase):
    def rodar(self, arquivos):
        r = subprocess.run([BASH, SCRIPTS + "/toca-executavel.sh"], input="\n".join(arquivos) + "\n",
                           capture_output=True, text=True)
        return r.returncode

    def test_docs_testes_e_automacao_nao_tocam(self):
        self.assertEqual(self.rodar(["README.md", "docs/processo.md", "tests/test_x.py", ".github/workflows/ci.yml",
                                     ".github/scripts/kanban.sh", "exemplos/a.rem"]), 1)

    def test_codigo_do_programa_toca(self):
        self.assertEqual(self.rodar(["README.md", "src/printroute/__main__.py"]), 0)
        self.assertEqual(self.rodar(["src/version.py"]), 0)

    def test_dependencias_empacotadas_tocam(self):
        self.assertEqual(self.rodar(["docs/a.md", "requirements-build.txt"]), 0)

    def test_compilador_e_instalador_tocam(self):
        # Bug real (tarefa #24): um PR que so mexia em build_exe.py foi marcado sem-executavel
        # e pulou a homologacao inteira, mesmo mudando o .exe de verdade. Mesmo bug depois
        # (tarefa #34): build_installer.py tambem nunca estava na lista.
        self.assertEqual(self.rodar(["packaging/windows/build_exe.py"]), 0)
        self.assertEqual(self.rodar(["docs/a.md", "packaging/windows/instalador.iss"]), 0)
        self.assertEqual(self.rodar(["packaging/windows/build_installer.py"]), 0)

    def test_nome_parecido_nao_conta(self):
        self.assertEqual(self.rodar(["docs/src/nota.md", "requirements-build.txt.bak", "tests/src/x.py",
                                     "packaging/windows/build_exe.py.bak"]), 1)

    def test_lista_vazia_sem_informacao(self):
        self.assertEqual(self.rodar([]), 2)


@unittest.skipUnless(USAVEL and JQ, "bash/git/jq utilizáveis não encontrados (ou Windows)")
class PublicarSemExecutavel(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.fix = os.path.join(self.tmp, "fix")
        self.bin = os.path.join(self.tmp, "bin")
        self.scripts = os.path.join(self.tmp, "scripts")
        for p in (self.fix, self.bin, self.scripts):
            os.makedirs(p)
        exec_(os.path.join(self.bin, "gh"), GH_FALSO)
        shutil.copy(SCRIPTS + "/publicar-sem-executavel.sh", self.scripts)
        exec_(os.path.join(self.scripts, "projeto.sh"), PROJETO_FALSO)

        # origin: main = develop + 2 commits de docs (nada em src/)
        self.origin = os.path.join(self.tmp, "origin.git")
        self.dono = os.path.join(self.tmp, "dono")
        self.git(self.tmp, "init", "-q", "--bare", "-b", "main", self.origin)
        os.makedirs(os.path.join(self.dono, "src"))
        self.git(self.dono, "init", "-q", "-b", "main")
        for k, v in (("user.name", "t"), ("user.email", "t@t"), ("core.autocrlf", "false")):
            self.git(self.dono, "config", k, v)
        self.git(self.dono, "remote", "add", "origin", self.origin)
        self.arquivo("src/app.py", "print('v1')\n")
        self.arquivo("requirements-build.txt", "pyinstaller\n")
        self.arquivo("README.md", "v1\n")
        self.commit("base")
        self.git(self.dono, "push", "-q", "origin", "main")
        self.git(self.dono, "checkout", "-q", "-b", "develop")
        self.arquivo("README.md", "v2\n")
        self.arquivo("docs.md", "novo\n")
        self.commit("docs")
        self.git(self.dono, "push", "-q", "origin", "develop")

        self.json("checks.json", {"check_runs": [{"name": "check", "status": "completed", "conclusion": "success"},
                                                {"name": "regras", "status": "completed", "conclusion": "success"}]})
        self.json("issues.json", [{"number": 46, "labels": [{"name": "task"}, {"name": "sem-executavel"}]},
                                  {"number": 50, "labels": [{"name": "bug"}, {"name": "sem-executavel"}]}])
        self.json("prs.json", [{"merged_at": "2026-01-01", "head": {"ref": "feature/46-docs"}},
                               {"merged_at": None, "head": {"ref": "feature/99-aberta"}}])
        self.cartoes("8", "Aprovado", [46])
        self.cartoes("9", "Aprovado", [50])

    # utilitários ---------------------------------------------------------
    def git(self, pasta, *args):
        r = subprocess.run([GIT, *args], cwd=pasta, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, f"git {args}: {r.stderr}")
        return r.stdout.strip()

    def arquivo(self, nome, texto, pasta=None):
        caminho = os.path.join(pasta or self.dono, nome)
        os.makedirs(os.path.dirname(caminho), exist_ok=True)
        with open(caminho, "w", encoding="utf-8", newline="\n") as f:
            f.write(texto)

    def commit(self, msg):
        self.git(self.dono, "add", ".")
        self.git(self.dono, "commit", "-q", "-m", msg)

    def json(self, nome, dado):
        with open(os.path.join(self.fix, nome), "w", encoding="utf-8") as f:
            json.dump(dado, f)

    def cartoes(self, painel, status, numeros):
        self.arquivo(f"cartoes_{painel}_{status}", "".join(f"{n}\n" for n in numeros), pasta=self.fix)

    def rodar(self, simular=False):
        runner = os.path.join(self.tmp, "runner")
        shutil.rmtree(runner, ignore_errors=True)
        self.git(self.tmp, "clone", "-q", self.origin, runner)
        for k, v in (("user.name", "t"), ("user.email", "t@t")):
            self.git(runner, "config", k, v)
        env = dict(os.environ, PATH=posix(self.bin) + os.pathsep + os.environ["PATH"], FIX=posix(self.fix),
                   GITHUB_REPOSITORY="o/r", PROJETO_PLANEJAMENTO="7", PROJETO_EXECUCAO="8", PROJETO_BUGS="9",
                   PROJETO_SH=posix(self.scripts + "/projeto.sh"), SIMULAR="true" if simular else "false")
        r = subprocess.run([BASH, posix(self.scripts + "/publicar-sem-executavel.sh")], cwd=runner, env=env,
                           capture_output=True, text=True)
        return r, r.stdout + r.stderr

    def chamadas(self):
        caminho = os.path.join(self.fix, "chamadas.log")
        if not os.path.exists(caminho):
            return []
        with open(caminho, encoding="utf-8") as f:
            return f.read().splitlines()

    def teve(self, trecho):
        return any(trecho in c for c in self.chamadas())

    def main_origem(self):
        return self.git(self.origin, "rev-parse", "main")

    def develop_origem(self):
        return self.git(self.origin, "rev-parse", "develop")

    # portão ---------------------------------------------------------------
    def test_simulacao_nao_altera_nada(self):
        antes = self.main_origem()
        r, saida = self.rodar(simular=True)
        self.assertEqual(r.returncode, 0, saida)
        self.assertIn("Portao aprovado", saida)
        self.assertIn("[simulado] avancar main", saida)
        self.assertIn("[simulado] fechar #46", saida)
        self.assertIn("[simulado] fechar #50", saida)
        self.assertEqual(self.main_origem(), antes)
        self.assertFalse(self.teve("gh issue close"))

    def test_mudanca_no_programa_recusa(self):
        self.arquivo("src/app.py", "print('v2')\n")
        self.commit("muda o programa")
        self.git(self.dono, "push", "-q", "origin", "develop")
        antes = self.main_origem()
        r, saida = self.rodar()
        self.assertEqual(r.returncode, 1, saida)
        self.assertIn("mudanca no programa", saida)
        self.assertIn("src/app.py", saida)
        self.assertEqual(self.main_origem(), antes)
        self.assertFalse(self.teve("gh issue close"))

    def test_dependencia_empacotada_recusa(self):
        self.arquivo("requirements-build.txt", "pyinstaller==7\n")
        self.commit("dep")
        self.git(self.dono, "push", "-q", "origin", "develop")
        r, saida = self.rodar()
        self.assertEqual(r.returncode, 1, saida)

    def test_main_divergente_recusa(self):
        self.git(self.dono, "checkout", "-q", "main")
        self.arquivo("hotfix.md", "so na main\n")
        self.commit("hotfix so na main")
        self.git(self.dono, "push", "-q", "origin", "main")
        r, saida = self.rodar()
        self.assertEqual(r.returncode, 1, saida)
        self.assertIn("divergiram", saida)

    def test_ci_da_develop_pendente_recusa(self):
        self.json("checks.json", {"check_runs": [{"name": "check", "status": "in_progress", "conclusion": None}]})
        r, saida = self.rodar()
        self.assertEqual(r.returncode, 1, saida)
        self.assertIn("pendente ou falhando", saida)
        self.json("checks.json", {"check_runs": []})
        r, saida = self.rodar()
        self.assertEqual(r.returncode, 1, saida)

    # publicação -----------------------------------------------------------
    def test_avanca_a_main_e_finaliza_as_issues_aprovadas(self):
        r, saida = self.rodar()
        self.assertEqual(r.returncode, 0, saida)
        self.assertEqual(self.main_origem(), self.develop_origem())  # fast-forward exato
        self.assertTrue(self.teve("gh issue close 46"))
        self.assertTrue(self.teve("gh issue close 50"))
        self.assertTrue(self.teve("projeto mover 8 46 Concluído"))
        self.assertTrue(self.teve("projeto mover 9 50 Corrigido"))
        self.assertTrue(self.teve("-X DELETE repos/o/r/git/refs/heads/feature/46-docs"))
        self.assertFalse(self.teve("feature/99-aberta"))  # PR não mesclado: branch fica

    def test_issue_fora_de_aprovado_segue_aberta(self):
        self.cartoes("8", "Aprovado", [])
        self.cartoes("8", "Homologação", [46])
        r, saida = self.rodar()
        self.assertEqual(r.returncode, 0, saida)
        self.assertIn("Seguem abertas", saida)
        self.assertFalse(self.teve("gh issue close 46"))
        self.assertTrue(self.teve("gh issue close 50"))

    def test_issue_reprovada_avisa_e_nao_fecha(self):
        self.cartoes("8", "Aprovado", [])
        self.cartoes("8", "Reprovado", [46])
        r, saida = self.rodar()
        self.assertEqual(r.returncode, 0, saida)
        self.assertIn("REPROVADAS", saida)
        self.assertFalse(self.teve("gh issue close 46"))

    def test_main_ja_atualizada_so_finaliza(self):
        self.git(self.dono, "push", "-q", "origin", "develop:main")
        r, saida = self.rodar()
        self.assertEqual(r.returncode, 0, saida)
        self.assertIn("ja esta na develop", saida)
        self.assertTrue(self.teve("gh issue close 46"))

    def test_sem_nenhuma_issue_ainda_avanca_a_main(self):
        self.json("issues.json", [])
        r, saida = self.rodar()
        self.assertEqual(r.returncode, 0, saida)
        self.assertEqual(self.main_origem(), self.develop_origem())
        self.assertFalse(self.teve("gh issue close"))


GH_PR = r'''#!/usr/bin/env bash
echo "gh $*" >> "$FIX/chamadas.log"
case "$1 $2" in
  "pr diff") cat "$FIX/diff.txt" ;;
esac
exit 0
'''


@unittest.skipUnless(USAVEL, "bash/git utilizáveis não encontrados (ou Windows)")
class PrRegrasMarcaSemExecutavel(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.bin = os.path.join(self.tmp, "bin")
        os.makedirs(self.bin)
        exec_(os.path.join(self.bin, "gh"), GH_PR)

    def rodar(self, arquivos, head="feature/35-algo", base="develop"):
        with open(os.path.join(self.tmp, "diff.txt"), "w", encoding="utf-8", newline="\n") as f:
            f.write("".join(a + "\n" for a in arquivos))
        env = dict(os.environ, PATH=posix(self.bin) + os.pathsep + os.environ["PATH"], FIX=posix(self.tmp),
                   HEAD_REF=head, BASE_REF=base, PR_TITLE="x", PR_BODY="Refs #35", PR_NUMBER="77",
                   BRANCH_DEVELOP="develop", BRANCH_MAIN="main")
        r = subprocess.run([BASH, SCRIPTS + "/pr-regras.sh"], env=env, capture_output=True, text=True)
        log = os.path.join(self.tmp, "chamadas.log")
        chamadas = []
        if os.path.exists(log):
            with open(log, encoding="utf-8") as f:
                chamadas = f.read().splitlines()
        return r, chamadas

    def test_pr_so_de_docs_marca_pr_e_issue(self):
        r, ch = self.rodar(["README.md", "docs/processo.md", "tests/test_a.py"])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("gh pr edit 77 --add-label sem-executavel", ch)
        self.assertIn("gh issue edit 35 --add-label sem-executavel", ch)

    def test_pr_que_toca_o_programa_retira_a_marca(self):
        r, ch = self.rodar(["README.md", "src/printroute/version.py"])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("gh pr edit 77 --remove-label sem-executavel", ch)
        self.assertIn("gh issue edit 35 --remove-label sem-executavel", ch)
        self.assertNotIn("gh pr edit 77 --add-label sem-executavel", ch)

    def test_diff_vazio_nao_mexe_na_marca(self):
        r, ch = self.rodar([])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertFalse(any("sem-executavel" in c for c in ch))

    def test_dependabot_de_actions_marca_so_o_pr(self):
        r, ch = self.rodar([".github/workflows/ci.yml"], head="dependabot/github_actions/develop/x-1")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("gh pr edit 77 --add-label sem-executavel", ch)
        self.assertFalse(any(c.startswith("gh issue edit") for c in ch))

    def test_pr_com_erro_de_regra_nao_marca(self):
        r, ch = self.rodar(["README.md"], head="minha-branch")
        self.assertNotEqual(r.returncode, 0)
        self.assertFalse(any("sem-executavel" in c for c in ch))


if __name__ == "__main__":
    unittest.main()
