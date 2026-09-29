"""encerrar-sprint.sh: no fim do encerramento de uma versão, a release/x.y.z é entregue ao
apagar-release.sh (que tem as travas). `gh`, `projeto.sh` e `apagar-release.sh` de mentira."""
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
case "$*" in
  *milestones\?*) json='[{"number":3,"title":"v0.2.0"}]' ;;
  *issues\?milestone*) json='[]' ;;
  *pulls\?state*) json='[]' ;;
  *) json='{}' ;;
esac
if [ -n "$filtro" ]; then jq -r "$filtro" <<<"$json"; else echo "$json"; fi
'''
PROJETO_FALSO = "#!/usr/bin/env bash\nexit 0\n"
APAGAR_FALSO = r'''#!/usr/bin/env bash
echo "apagar-release VERSAO=$VERSAO SIMULAR=$SIMULAR" >> "$FIX/chamadas.log"
[ ! -f "$FIX/apagar_falha" ] || exit 1
'''


@unittest.skipUnless(USAVEL and shutil.which("jq"), "bash/git/jq indisponíveis (roda no job scripts (Linux) do CI)")
class EncerrarApagaRelease(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.fix = os.path.join(self.tmp, "fix")
        self.bin = os.path.join(self.tmp, "bin")
        self.scripts = os.path.join(self.tmp, "scripts")
        for p in (self.fix, self.bin, self.scripts):
            os.makedirs(p)
        shutil.copy(os.path.join(SCRIPTS, "encerrar-sprint.sh"), self.scripts)
        self.exec_(os.path.join(self.bin, "gh"), GH_FALSO)
        self.exec_(os.path.join(self.scripts, "projeto.sh"), PROJETO_FALSO)
        self.exec_(os.path.join(self.scripts, "apagar-release.sh"), APAGAR_FALSO)

    def exec_(self, caminho, texto):
        with open(caminho, "w", encoding="utf-8", newline="\n") as f:
            f.write(texto)
        os.chmod(caminho, os.stat(caminho).st_mode | stat.S_IXUSR)

    def rodar(self, simular=False):
        env = dict(os.environ, PATH=posix(self.bin) + os.pathsep + os.environ["PATH"], FIX=posix(self.fix),
                   GITHUB_REPOSITORY="dono/repo", PROJETO_PLANEJAMENTO="10", PROJETO_EXECUCAO="11",
                   PROJETO_BUGS="12", VERSAO="v0.2.0", SIMULAR="true" if simular else "false")
        r = subprocess.run([BASH, posix(os.path.join(self.scripts, "encerrar-sprint.sh"))], env=env,
                           capture_output=True, text=True)
        with open(os.path.join(self.fix, "chamadas.log"), encoding="utf-8") as f:
            return r, r.stdout + r.stderr, f.read().splitlines()

    def test_entrega_a_release_da_versao_ao_apagar_release_no_fim(self):
        r, saida, chamadas = self.rodar()
        self.assertEqual(r.returncode, 0, saida)
        self.assertEqual(chamadas[-1], "apagar-release VERSAO=0.2.0 SIMULAR=false")
        self.assertTrue(saida.rstrip().endswith("Sprint v0.2.0 encerrada."))

    def test_simulacao_repassa_o_simular(self):
        r, saida, chamadas = self.rodar(simular=True)
        self.assertEqual(r.returncode, 0, saida)
        self.assertIn("apagar-release VERSAO=0.2.0 SIMULAR=true", chamadas)

    def test_falha_ao_apagar_nao_derruba_o_encerramento(self):
        open(os.path.join(self.fix, "apagar_falha"), "w").close()
        r, saida, _ = self.rodar()
        self.assertEqual(r.returncode, 0, saida)
        self.assertIn("Nao consegui conferir/apagar release/0.2.0", saida)
        self.assertIn("Sprint v0.2.0 encerrada.", saida)


if __name__ == "__main__":
    unittest.main()
