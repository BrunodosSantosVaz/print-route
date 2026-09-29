"""publicar-producao.sh: o portão da publicação (cartões aprovados, PR limpo, candidata testada) e a
ordem das etapas. Usa git de verdade (origin + clone) e um `gh` de mentira que responde com JSONs de
fixture (o filtro --jq roda de verdade no jq) e registra as chamadas."""
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
  "release view "*) [ -f "$FIX/publicada" ] || exit 1 ;;
  "api repos/o/r/milestones"*) emitir "$FIX/milestones.json" ;;
  "api repos/o/r/issues?milestone"*) emitir "$FIX/issues.json" ;;
  "pr list"*) emitir "$FIX/prlist.json" ;;
  "pr view"*) emitir "$FIX/prview.json" ;;
esac
exit 0
'''

PROJETO_FALSO = r'''#!/usr/bin/env bash
# projeto.sh cartoes <painel> <status>
[ "$1" = cartoes ] || exit 0
f="$FIX/cartoes_$2_$3"
[ ! -f "$f" ] || cat "$f"
'''

ETAPA_FALSA = r'''#!/usr/bin/env bash
echo "etapa $(basename "$0") VERSAO=${VERSAO:-} TAG=${TAG:-} RC_TAG=${RC_TAG:-} TARGET_SHA=${TARGET_SHA:+ok} SIMULAR=${SIMULAR:-} DRY_RUN=${DRY_RUN:-}" >> "$FIX/chamadas.log"
'''


def escrever_exec(caminho, texto):
    with open(caminho, "w", encoding="utf-8", newline="\n") as f:
        f.write(texto)
    os.chmod(caminho, os.stat(caminho).st_mode | stat.S_IXUSR)


@unittest.skipUnless(USAVEL and JQ, "bash/git/jq utilizáveis não encontrados (ou Windows)")
class PublicarProducao(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.fix = os.path.join(self.tmp, "fix")
        os.makedirs(self.fix)
        bin_ = os.path.join(self.tmp, "bin")
        os.makedirs(bin_)
        escrever_exec(os.path.join(bin_, "gh"), GH_FALSO)
        self.bin = bin_
        # scripts sob teste (copiados) + etapas de mentira
        self.scripts = os.path.join(self.tmp, "scripts")
        os.makedirs(self.scripts)
        for nome in ("publicar-producao.sh", "conferir-release.sh", "versao.sh"):
            shutil.copy(os.path.join(SCRIPTS, nome), self.scripts)
        for nome in ("promover-release.sh", "anunciar-release.sh", "encerrar-sprint.sh", "backmerge.sh"):
            escrever_exec(os.path.join(self.scripts, nome), ETAPA_FALSA)
        escrever_exec(os.path.join(self.scripts, "projeto.sh"), PROJETO_FALSO)

        # repositório: main já com a versão (é como fica depois do merge), release/0.2.0 igual + tag da rc
        self.origin = os.path.join(self.tmp, "origin.git")
        dono = os.path.join(self.tmp, "dono")
        self.git(self.tmp, "init", "-q", "--bare", "-b", "main", self.origin)
        os.makedirs(os.path.join(dono, "src", "printroute"))
        os.makedirs(os.path.join(dono, "packaging", "windows"))
        self.git(dono, "init", "-q", "-b", "main")
        for k, v in (("user.name", "t"), ("user.email", "t@t"), ("core.autocrlf", "false")):
            self.git(dono, "config", k, v)
        self.git(dono, "remote", "add", "origin", self.origin)
        self.arquivo(dono, "src/printroute/version.py", '__version__ = "0.2.0"\n')
        self.arquivo(dono, "packaging/windows/build_exe.py", "# build\n")
        self.arquivo(dono, "requirements-build.txt", "pyinstaller\n")
        self.arquivo(dono, "CHANGELOG.md", "# Changelog\n\n## [0.2.0] - 2026-01-01\n- algo\n")
        self.git(dono, "add", ".")
        self.git(dono, "commit", "-q", "-m", "release 0.2.0")
        self.git(dono, "tag", "v0.2.0-rc.1")
        self.git(dono, "push", "-q", "origin", "main", "main:release/0.2.0", "v0.2.0-rc.1")
        self.dono = dono

        # cenário feliz: 2 tarefas + 1 bug aprovados, PR aberto e limpo
        self.issues([(1, "open", "task"), (2, "open", "task"), (3, "open", "bug")])
        self.cartoes("8", "Aprovado", [1, 2])
        self.cartoes("9", "Aprovado", [3])
        self.json("milestones.json", [{"title": "v0.2.0", "number": 5}, {"title": "v0.1.0", "number": 1}])
        self.json("prlist.json", [{"number": 70, "state": "OPEN"}])
        self.pr_view("MERGEABLE", [{"name": "check", "status": "COMPLETED", "conclusion": "SUCCESS"},
                                   {"context": "regras", "state": "SUCCESS"}])

    # utilitários ---------------------------------------------------------
    def git(self, pasta, *args):
        r = subprocess.run([GIT, *args], cwd=pasta, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, f"git {args}: {r.stderr}")
        return r.stdout.strip()

    def arquivo(self, pasta, nome, texto):
        caminho = os.path.join(pasta, nome)
        with open(caminho, "w", encoding="utf-8", newline="\n") as f:
            f.write(texto)

    def json(self, nome, dado):
        with open(os.path.join(self.fix, nome), "w", encoding="utf-8") as f:
            json.dump(dado, f)

    def issues(self, itens):
        self.json("issues.json", [
            {"number": n, "state": estado, "labels": [{"name": tipo}]} for n, estado, tipo in itens])

    def cartoes(self, painel, status, numeros):
        self.arquivo(self.fix, f"cartoes_{painel}_{status}", "".join(f"{n}\n" for n in numeros))

    def pr_view(self, mergeable, checks):
        self.json("prview.json", {"mergeable": mergeable, "statusCheckRollup": checks})

    def rodar(self, simular=True, versao="v0.2.0"):
        runner = os.path.join(self.tmp, "runner")
        shutil.rmtree(runner, ignore_errors=True)
        self.git(self.tmp, "clone", "-q", self.origin, runner)
        for k, v in (("user.name", "t"), ("user.email", "t@t"), ("core.autocrlf", "false")):
            self.git(runner, "config", k, v)
        env = dict(os.environ, PATH=posix(self.bin) + os.pathsep + os.environ["PATH"], FIX=posix(self.fix),
                   GITHUB_REPOSITORY="o/r", PROJETO_PLANEJAMENTO="7", PROJETO_EXECUCAO="8", PROJETO_BUGS="9",
                   PROJETO_SH=posix(self.scripts + "/projeto.sh"), VERSAO=versao, SIMULAR="true" if simular else "false",
                   GITHUB_OUTPUT=os.devnull)
        r = subprocess.run([BASH, posix(self.scripts + "/publicar-producao.sh")], cwd=runner, env=env,
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

    # portão ---------------------------------------------------------------
    def test_simulacao_feliz_nao_altera_nada(self):
        r, saida = self.rodar(simular=True)
        self.assertEqual(r.returncode, 0, saida)
        self.assertIn("Portao aprovado: candidata v0.2.0-rc.1", saida)
        self.assertIn("[simulado] mesclar PR #70", saida)
        self.assertFalse(self.teve("pr merge"))
        self.assertFalse(self.teve("promover-release"))
        # a limpeza é chamada só em modo simulado
        self.assertTrue(self.teve("etapa encerrar-sprint.sh VERSAO=0.2.0 TAG= RC_TAG= TARGET_SHA= SIMULAR=true"))

    def test_cartao_pendente_recusa(self):
        self.cartoes("8", "Aprovado", [1])  # a #2 ficou de fora
        r, saida = self.rodar()
        self.assertEqual(r.returncode, 1, saida)
        self.assertIn("ainda nao aprovados", saida)
        self.assertIn("#2", saida)
        self.assertIn("RECUSADA", saida)

    def test_cartao_reprovado_recusa_e_orienta(self):
        self.cartoes("8", "Aprovado", [1])
        self.cartoes("8", "Reprovado", [2])
        r, saida = self.rodar()
        self.assertEqual(r.returncode, 1, saida)
        self.assertIn("REPROVADOS na homologacao: #2", saida)
        self.assertIn("Criar branches", saida)

    def test_bug_precisa_estar_aprovado_no_painel_de_bugs(self):
        self.cartoes("9", "Aprovado", [])
        r, saida = self.rodar()
        self.assertEqual(r.returncode, 1, saida)
        self.assertIn("#3", saida)

    def test_issue_ja_fechada_conta_como_concluida(self):
        self.issues([(1, "closed", "task"), (2, "open", "task"), (3, "open", "bug")])
        self.cartoes("8", "Aprovado", [2])
        r, saida = self.rodar()
        self.assertEqual(r.returncode, 0, saida)

    def test_milestone_inexistente_ou_vazio_recusa(self):
        self.json("milestones.json", [{"title": "v0.1.0", "number": 1}])
        r, saida = self.rodar()
        self.assertEqual(r.returncode, 1, saida)
        self.assertIn("Milestone 'v0.2.0' nao encontrado", saida)
        self.json("milestones.json", [{"title": "v0.2.0", "number": 5}])
        self.issues([])
        r, saida = self.rodar()
        self.assertEqual(r.returncode, 1, saida)
        self.assertIn("nao tem tarefas nem bugs", saida)

    def test_epicos_do_milestone_nao_contam_como_tarefas(self):
        self.json("issues.json", [
            {"number": 1, "state": "open", "labels": [{"name": "task"}]},
            {"number": 4, "state": "open", "labels": [{"name": "epic"}]},
            {"number": 99, "state": "open", "labels": [{"name": "task"}], "pull_request": {}},
        ])
        self.cartoes("8", "Aprovado", [1])
        r, saida = self.rodar()
        self.assertEqual(r.returncode, 0, saida)

    def test_sem_pr_da_release_recusa(self):
        self.json("prlist.json", [])
        r, saida = self.rodar()
        self.assertEqual(r.returncode, 1, saida)
        self.assertIn("Nao ha PR release/0.2.0", saida)

    def test_pr_com_conflito_recusa(self):
        self.pr_view("CONFLICTING", [])
        r, saida = self.rodar()
        self.assertEqual(r.returncode, 1, saida)
        self.assertIn("tem conflito", saida)

    def test_checks_falhando_ou_pendentes_recusam(self):
        self.pr_view("MERGEABLE", [{"name": "check", "status": "COMPLETED", "conclusion": "FAILURE"},
                                   {"name": "compat", "status": "IN_PROGRESS", "conclusion": ""},
                                   {"name": "codeql", "status": "COMPLETED", "conclusion": "SKIPPED"}])
        r, saida = self.rodar()
        self.assertEqual(r.returncode, 1, saida)
        self.assertIn("check, compat", saida)
        self.assertNotIn("codeql", saida.split("pendentes ou falhando:")[1])

    def test_codigo_alterado_depois_da_candidata_recusa(self):
        self.arquivo(self.dono, "src/printroute/version.py", '__version__ = "0.2.0"\n# mudou\n')
        self.git(self.dono, "commit", "-q", "-am", "mudou depois da rc")
        self.git(self.dono, "push", "-q", "origin", "main:release/0.2.0")
        r, saida = self.rodar()
        self.assertEqual(r.returncode, 1, saida)
        self.assertIn("O codigo mudou depois da candidata", saida)

    def test_sem_secao_no_changelog_recusa(self):
        self.arquivo(self.dono, "CHANGELOG.md", "# Changelog\n\n## [0.1.0]\n")
        self.git(self.dono, "commit", "-q", "-am", "changelog")
        self.git(self.dono, "push", "-q", "origin", "main:release/0.2.0")
        r, saida = self.rodar()
        self.assertEqual(r.returncode, 1, saida)
        self.assertIn("sem a secao", saida)

    def test_branch_da_release_inexistente_recusa(self):
        self.git(self.dono, "push", "-q", "origin", ":release/0.2.0")
        r, saida = self.rodar()
        self.assertEqual(r.returncode, 1, saida)
        self.assertIn("Branch release/0.2.0 nao encontrada", saida)

    # publicação -----------------------------------------------------------
    def test_publicacao_real_segue_a_ordem(self):
        r, saida = self.rodar(simular=False)
        self.assertEqual(r.returncode, 0, saida)
        etapas = [c for c in self.chamadas() if c.startswith("etapa ") or c.startswith("gh pr merge")]
        nomes = [c.split()[1] if c.startswith("etapa") else "merge" for c in etapas]
        self.assertEqual(nomes, ["merge", "promover-release.sh", "anunciar-release.sh",
                                 "encerrar-sprint.sh", "backmerge.sh"])
        merge = next(c for c in etapas if c.startswith("gh pr merge"))
        self.assertIn("--merge --admin", merge)
        self.assertIn("chore(release): merge v0.2.0", merge)
        promover = next(c for c in etapas if "promover-release" in c)
        self.assertIn("RC_TAG=v0.2.0-rc.1", promover)
        self.assertIn("TARGET_SHA=ok", promover)
        encerrar = next(c for c in etapas if "encerrar-sprint" in c)
        self.assertIn("SIMULAR=false", encerrar)

    def test_pr_ja_mesclado_nao_mescla_de_novo(self):
        self.json("prlist.json", [{"number": 70, "state": "MERGED"}])
        r, saida = self.rodar(simular=False)
        self.assertEqual(r.returncode, 0, saida)
        self.assertFalse(self.teve("gh pr merge"))
        self.assertTrue(self.teve("promover-release.sh"))

    def test_release_ja_publicada_so_finaliza(self):
        self.arquivo(self.fix, "publicada", "")
        self.cartoes("8", "Aprovado", [])  # ninguém precisa estar aprovado numa retomada
        r, saida = self.rodar(simular=False)
        self.assertEqual(r.returncode, 0, saida)
        self.assertIn("ja existe", saida)
        self.assertFalse(self.teve("gh pr merge"))
        self.assertFalse(self.teve("promover-release.sh"))
        self.assertTrue(self.teve("encerrar-sprint.sh"))
        self.assertTrue(self.teve("backmerge.sh"))

    def test_recusa_nao_chama_nenhuma_etapa(self):
        self.cartoes("8", "Aprovado", [])
        r, saida = self.rodar(simular=False)
        self.assertEqual(r.returncode, 1, saida)
        self.assertFalse(self.teve("gh pr merge"))
        self.assertFalse(any(c.startswith("etapa ") for c in self.chamadas()))

    def test_versao_aceita_com_ou_sem_v(self):
        r, saida = self.rodar(versao="0.2.0")
        self.assertEqual(r.returncode, 0, saida)


if __name__ == "__main__":
    unittest.main()
