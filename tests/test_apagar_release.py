"""apagar-release.sh: a branch release/x.y.z só é apagada com todas as travas satisfeitas (tag, Release,
branch contida na tag e na main), e nenhuma tag é tocada. `gh` de mentira controlado por arquivos."""
import os
import shutil
import stat
import subprocess
import tempfile
import unittest

import _caminho
from _bash import BASH, USAVEL, posix

SCRIPT = posix(os.path.join(_caminho.RAIZ, ".github", "scripts", "apagar-release.sh"))

# Arquivos em $FIX: sem_branch, sem_tag, sem_release (existem => falta aquilo); fora_tag, fora_main
# (conteúdo = ahead_by). O --jq é aplicado com jq de verdade.
GH_FALSO = r'''#!/usr/bin/env bash
printf 'gh %s\n' "$(printf '%q ' "$@")" >> "$FIX/chamadas.log"
filtro=""
args=("$@")
for ((i = 0; i < ${#args[@]}; i++)); do [ "${args[i]}" = --jq ] && filtro="${args[i+1]}"; done
responder() { if [ -n "$filtro" ]; then jq -r "$filtro" <<<"$1"; else echo "$1"; fi; }
case "$*" in
  "release view"*) [ -f "$FIX/sem_release" ] && exit 1; exit 0 ;;
  *"-X DELETE"*) exit 0 ;;
  *git/ref/heads/*) [ -f "$FIX/sem_branch" ] && exit 1; responder '{"ref":"x"}' ;;
  *git/ref/tags/*) [ -f "$FIX/sem_tag" ] && exit 1; responder '{"ref":"x"}' ;;
  *compare/main...*) responder "{\"ahead_by\":$(cat "$FIX/fora_main" 2>/dev/null || echo 0)}" ;;
  *compare/v*) responder "{\"ahead_by\":$(cat "$FIX/fora_tag" 2>/dev/null || echo 0)}" ;;
  *) responder '{}' ;;
esac
'''


@unittest.skipUnless(USAVEL and shutil.which("jq"), "bash/git/jq indisponíveis (roda no job scripts (Linux) do CI)")
class ApagarRelease(unittest.TestCase):
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

    def marcar(self, nome, conteudo=""):
        with open(os.path.join(self.fix, nome), "w", encoding="utf-8") as f:
            f.write(conteudo)

    def rodar(self, versao="v0.2.0", simular=False):
        env = dict(os.environ, PATH=posix(self.bin) + os.pathsep + os.environ["PATH"], FIX=posix(self.fix),
                   GITHUB_REPOSITORY="dono/repo", VERSAO=versao, SIMULAR="true" if simular else "false")
        r = subprocess.run([BASH, SCRIPT], env=env, capture_output=True, text=True)
        return r, r.stdout + r.stderr

    def chamadas(self):
        caminho = os.path.join(self.fix, "chamadas.log")
        if not os.path.exists(caminho):
            return []
        with open(caminho, encoding="utf-8") as f:
            return f.read().splitlines()

    def apagou(self):
        return [c for c in self.chamadas() if "DELETE" in c]

    def test_todas_as_travas_ok_apaga_so_a_branch(self):
        r, saida = self.rodar()
        self.assertEqual(r.returncode, 0, saida)
        self.assertEqual(len(self.apagou()), 1)
        self.assertIn("repos/dono/repo/git/refs/heads/release/0.2.0", self.apagou()[0])
        self.assertIn("Branch apagada: release/0.2.0", saida)
        self.assertIn("Conferindo release/0.2.0 antes de apagar:", saida)  # sem "false" colado no texto

    def test_nenhuma_chamada_toca_tag_para_escrever(self):
        self.rodar()
        for c in self.chamadas():
            if "-X" in c:
                self.assertNotIn("tags", c)

    def test_cada_trava_que_falha_mantem_a_branch(self):
        casos = {
            "sem_tag": ("", "a tag v0.2.0 nao existe"),
            "sem_release": ("", "a Release v0.2.0 nao existe"),
            "fora_tag": ("2", "2 commit(s) da branch nao estao na tag v0.2.0"),
            "fora_main": ("1", "1 commit(s) da branch nao estao na main"),
        }
        for arquivo, (conteudo, motivo) in casos.items():
            with self.subTest(trava=arquivo):
                for f in os.listdir(self.fix):
                    os.remove(os.path.join(self.fix, f))
                self.marcar(arquivo, conteudo)
                r, saida = self.rodar()
                self.assertEqual(r.returncode, 0, saida)  # aviso, sem derrubar a publicacao
                self.assertIn(f"release/0.2.0 mantida: {motivo}", saida)
                self.assertEqual(self.apagou(), [])

    def test_simulacao_confere_e_nao_apaga(self):
        r, saida = self.rodar(simular=True)
        self.assertEqual(r.returncode, 0, saida)
        self.assertIn("[simulado] apagar release/0.2.0", saida)
        self.assertEqual(self.apagou(), [])

    def test_branch_inexistente_nao_e_erro(self):
        self.marcar("sem_branch")
        r, saida = self.rodar()
        self.assertEqual(r.returncode, 0, saida)
        self.assertIn("ja nao existe", saida)
        self.assertEqual(self.apagou(), [])

    def test_versao_invalida_nao_apaga_nada(self):
        for versao in ("v0.2.0-rc.1", "0.2", "*", "0.2.0/../main"):
            with self.subTest(versao=versao):
                r, saida = self.rodar(versao=versao)
                self.assertEqual(r.returncode, 2, saida)
                self.assertEqual(self.apagou(), [])


if __name__ == "__main__":
    unittest.main()
