"""Nome dos arquivos gerados pelo build (candidata x produção). Não roda o PyInstaller."""
import unittest

import _caminho  # noqa: F401
import build_exe
from printroute.version import __version__


class NomeDoArquivo(unittest.TestCase):
    def test_producao_nao_tem_sufixo(self):
        self.assertEqual(build_exe.nome_do_arquivo(), f"PrintRoute-v{__version__}-windows-x64.exe")

    def test_candidata_leva_rc_no_nome(self):
        self.assertEqual(build_exe.nome_do_arquivo(3), f"PrintRoute-v{__version__}-rc.3-windows-x64.exe")

    def test_versao_e_semver(self):
        partes = __version__.split(".")
        self.assertEqual(len(partes), 3)
        self.assertTrue(all(p.isdigit() for p in partes))


if __name__ == "__main__":
    unittest.main()
