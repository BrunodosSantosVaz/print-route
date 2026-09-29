"""Testes de src/printroute/spooler/gerenciar.py: instala e remove de verdade a
impressora PrintRoute no Windows. Só faz sentido no Windows (usa PowerShell e o
spooler) -- roda nos jobs "check" e "compat" da CI (windows-latest); no resto, pula."""
import sys
import unittest

import _caminho  # noqa: F401

_TEM_WINDOWS = sys.platform == "win32"

if _TEM_WINDOWS:
    from printroute.spooler import gerenciar


@unittest.skipUnless(_TEM_WINDOWS, "gerenciar.py só funciona no Windows (usa PowerShell/spooler)")
class InstalarEDesinstalar(unittest.TestCase):
    def tearDown(self):
        gerenciar.desinstalar()

    def test_instala_a_porta_e_a_impressora(self):
        gerenciar.instalar()
        self.assertTrue(gerenciar.porta_existe())
        self.assertTrue(gerenciar.impressora_existe())

    def test_instalar_duas_vezes_nao_falha_nem_duplica(self):
        gerenciar.instalar()
        gerenciar.instalar()
        self.assertTrue(gerenciar.impressora_existe())

    def test_desinstalar_remove_a_impressora_e_a_porta(self):
        gerenciar.instalar()
        gerenciar.desinstalar()
        self.assertFalse(gerenciar.impressora_existe())
        self.assertFalse(gerenciar.porta_existe())

    def test_desinstalar_sem_estar_instalado_nao_falha(self):
        gerenciar.desinstalar()
        self.assertFalse(gerenciar.impressora_existe())


if __name__ == "__main__":
    unittest.main()
