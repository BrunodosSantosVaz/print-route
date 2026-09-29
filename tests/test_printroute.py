"""O pacote printroute: versão legível e em formato SemVer."""
import unittest

import _caminho  # noqa: F401
from printroute.version import __version__


class Versao(unittest.TestCase):
    def test_e_semver(self):
        self.assertRegex(__version__, r"^\d+\.\d+\.\d+$")

    def test_importa_o_pacote(self):
        import printroute
        self.assertTrue(printroute.__doc__)


if __name__ == "__main__":
    unittest.main()
