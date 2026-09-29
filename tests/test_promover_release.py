"""promover-release.sh: promove a release candidata a versão de produção SEM recompilar (mesmo binário,
mesmo SHA-256), com `gh` de mentira que registra as chamadas."""
import hashlib
import os
import shutil
import stat
import subprocess
import tempfile
import unittest

import _caminho
from _bash import BASH, GIT, posix, USAVEL

SCRIPT = posix(_caminho.RAIZ + "/.github/scripts/promover-release.sh")
BINARIO = b"MZ conteudo do exe testado em homologacao"

GH_FALSO = r'''#!/usr/bin/env bash
echo "gh $*" >> "$FIX/chamadas.log"
case "$1 $2" in
  "release view") [ -f "$FIX/publicada" ] || exit 1 ;;
  "release download")
    dir=""; args=("$@")
    for ((i = 0; i < ${#args[@]}; i++)); do [ "${args[i]}" = --dir ] && dir="${args[i+1]}"; done
    mkdir -p "$dir"
    cp "$FIX/binario" "$dir/PrintRoute-$3-windows-x64.exe"
    (cd "$dir" && sha256sum "PrintRoute-$3-windows-x64.exe" > SHA256SUMS.txt)
    [ ! -f "$FIX/adulterar" ] || echo adulterado >> "$dir/PrintRoute-$3-windows-x64.exe" ;;
  "release create")  # guarda os arquivos anexados, como a Release os receberia
    mkdir -p "$FIX/publicado"
    for a in "$@"; do [ ! -f "$a" ] || [ "$a" = notas.md ] || cp "$a" "$FIX/publicado/"; done ;;
esac
exit 0
'''


@unittest.skipUnless(USAVEL, "bash/git utilizáveis não encontrados (ou Windows)")
class PromoverRelease(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.fix = os.path.join(self.tmp, "fix")
        self.bin = os.path.join(self.tmp, "bin")
        self.repo = os.path.join(self.tmp, "repo")
        for p in (self.fix, self.bin, os.path.join(self.repo, "src", "printroute")):
            os.makedirs(p)
        gh = os.path.join(self.bin, "gh")
        with open(gh, "w", encoding="utf-8", newline="\n") as f:
            f.write(GH_FALSO)
        os.chmod(gh, os.stat(gh).st_mode | stat.S_IXUSR)
        with open(os.path.join(self.fix, "binario"), "wb") as f:
            f.write(BINARIO)
        self.escrever("src/printroute/version.py", '__version__ = "0.2.0"\n')
        self.escrever("CHANGELOG.md", "# Changelog\n\n## [0.3.0]\n- futuro\n\n## [0.2.0] - 2026-01-01\n### Adicionado\n- campo novo\n\n## [0.1.0]\n- antigo\n")
        for args in (("init", "-q", "-b", "main"), ("config", "user.email", "t@t"), ("config", "user.name", "t"),
                     ("add", "."), ("commit", "-q", "-m", "x")):
            subprocess.run([GIT, *args], cwd=self.repo, check=True, capture_output=True)

    def escrever(self, nome, texto):
        with open(os.path.join(self.repo, nome), "w", encoding="utf-8", newline="\n") as f:
            f.write(texto)

    def rodar(self, **extra):
        saida = os.path.join(self.tmp, "gh_output")
        open(saida, "w").close()
        env = dict(os.environ, PATH=posix(self.bin) + os.pathsep + os.environ["PATH"], FIX=posix(self.fix),
                   RC_TAG="v0.2.0-rc.3", GITHUB_REPOSITORY="o/r", GITHUB_OUTPUT=posix(saida), **extra)
        r = subprocess.run([BASH, SCRIPT], cwd=self.repo, env=env, capture_output=True, text=True)
        with open(saida, encoding="utf-8") as f:
            return r, f.read().split()

    def chamadas(self):
        with open(os.path.join(self.fix, "chamadas.log"), encoding="utf-8") as f:
            return f.read().splitlines()

    def test_promove_o_mesmo_binario_com_nome_de_producao(self):
        r, saidas = self.rodar()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(sorted(saidas), ["nova=true", "tag=v0.2.0"])
        publicado = os.path.join(self.fix, "publicado")
        self.assertEqual(sorted(os.listdir(publicado)), ["PrintRoute-v0.2.0-windows-x64.exe", "SHA256SUMS.txt"])
        with open(os.path.join(publicado, "PrintRoute-v0.2.0-windows-x64.exe"), "rb") as f:
            self.assertEqual(f.read(), BINARIO)  # nada de recompilar: os bytes são os da candidata
        hash_ = hashlib.sha256(BINARIO).hexdigest()
        with open(os.path.join(publicado, "SHA256SUMS.txt"), encoding="utf-8") as f:
            self.assertEqual(f.read().split(), [hash_, "PrintRoute-v0.2.0-windows-x64.exe"])

    def test_executavel_fica_so_na_release_e_nada_e_gravado_no_repositorio(self):
        r, _ = self.rodar()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertFalse(os.path.exists(os.path.join(self.repo, "releases")))
        self.assertFalse(os.path.exists(os.path.join(self.repo, "baixado")))
        status = subprocess.run([GIT, "status", "--porcelain"], cwd=self.repo, capture_output=True, text=True).stdout
        self.assertEqual([linha for linha in status.splitlines() if not linha.endswith("notas.md")], [])

    def test_notas_sao_a_secao_da_versao_e_citam_a_candidata(self):
        self.rodar(TARGET_SHA="abc123")
        with open(os.path.join(self.repo, "notas.md"), encoding="utf-8") as f:
            notas = f.read()
        self.assertIn("campo novo", notas)
        self.assertNotIn("futuro", notas)
        self.assertNotIn("antigo", notas)
        self.assertIn("v0.2.0-rc.3", notas)
        self.assertIn(hashlib.sha256(BINARIO).hexdigest(), notas)

    def test_cria_a_release_como_latest_no_commit_indicado(self):
        self.rodar(TARGET_SHA="abc123")
        criar = next(c for c in self.chamadas() if c.startswith("gh release create"))
        self.assertIn("v0.2.0 ", criar)
        self.assertIn("--target abc123", criar)
        self.assertIn("--latest", criar)
        self.assertNotIn("--latest=false", criar)
        self.assertIn("PrintRoute-v0.2.0-windows-x64.exe", criar)

    def test_ensaio_nao_marca_latest(self):
        self.rodar(TARGET_SHA="abc123", RELEASE_LATEST="false")
        criar = next(c for c in self.chamadas() if c.startswith("gh release create"))
        self.assertIn("--latest=false", criar)

    def test_release_existente_nao_publica_de_novo(self):
        open(os.path.join(self.fix, "publicada"), "w").close()
        r, saidas = self.rodar()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("nova=false", saidas)
        self.assertFalse(any(c.startswith("gh release create") for c in self.chamadas()))
        self.assertFalse(os.path.exists(os.path.join(self.repo, "releases")))

    def test_hash_divergente_da_candidata_aborta(self):
        open(os.path.join(self.fix, "adulterar"), "w").close()
        r, _ = self.rodar()
        self.assertNotEqual(r.returncode, 0)
        self.assertFalse(any(c.startswith("gh release create") for c in self.chamadas()))


if __name__ == "__main__":
    unittest.main()
