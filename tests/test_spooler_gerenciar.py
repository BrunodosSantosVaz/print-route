"""Testes de src/printroute/spooler/gerenciar.py.

`EscolherPorta` mocka `_powershell`: é lógica pura (comparação de nomes), roda em
qualquer sistema. O resto instala e remove de verdade a impressora PrintRoute no
Windows -- só faz sentido lá (usa PowerShell e o spooler) -- roda nos jobs "check" e
"compat" da CI (windows-latest); no resto, pula."""
import sys
import unittest
from unittest import mock

import _caminho  # noqa: F401
from printroute.spooler import gerenciar

_TEM_WINDOWS = sys.platform == "win32"


class EscolherPorta(unittest.TestCase):
    """Bug real (achado testando o instalador num Windows 11, não só na CI): o Windows
    devolve os nomes de porta clássicos em caixa diferente conforme a instalação (ex.:
    "nul:", não "NUL:"), e a comparação exata nunca batia -- a escolha caía para
    "FILE:", que pede um caminho a cada impressão e nunca deixa o trabalho terminar."""

    @mock.patch("printroute.spooler.gerenciar._powershell")
    def test_ignora_a_caixa_e_devolve_o_nome_real_do_sistema(self, _powershell):
        _powershell.return_value = '["COM1:","FILE:","nul:","LPT1:"]'
        self.assertEqual(gerenciar._escolher_porta(), "nul:")

    @mock.patch("printroute.spooler.gerenciar._powershell")
    def test_bate_mesmo_na_mesma_caixa(self, _powershell):
        _powershell.return_value = '["FILE:","NUL:"]'
        self.assertEqual(gerenciar._escolher_porta(), "NUL:")

    @mock.patch("printroute.spooler.gerenciar._powershell")
    def test_sem_candidato_conhecido_usa_a_primeira_porta_do_sistema(self, _powershell):
        _powershell.return_value = '["AD_Port","USB001"]'
        self.assertEqual(gerenciar._escolher_porta(), "AD_Port")

    @mock.patch("printroute.spooler.gerenciar._powershell")
    def test_sem_porta_nenhuma_no_sistema_falha(self, _powershell):
        _powershell.return_value = ""
        with self.assertRaises(gerenciar.ErroDoPowerShell):
            gerenciar._escolher_porta()


@unittest.skipUnless(_TEM_WINDOWS, "gerenciar.py só funciona no Windows (usa PowerShell/spooler)")
class InstalarEDesinstalar(unittest.TestCase):
    def tearDown(self):
        gerenciar.desinstalar()

    def test_instala_a_impressora(self):
        gerenciar.instalar()
        self.assertTrue(gerenciar.impressora_existe())

    def test_instalar_duas_vezes_nao_falha_nem_duplica(self):
        gerenciar.instalar()
        gerenciar.instalar()
        self.assertTrue(gerenciar.impressora_existe())

    def test_desinstalar_remove_a_impressora(self):
        gerenciar.instalar()
        gerenciar.desinstalar()
        self.assertFalse(gerenciar.impressora_existe())

    def test_desinstalar_sem_estar_instalado_nao_falha(self):
        gerenciar.desinstalar()
        self.assertFalse(gerenciar.impressora_existe())


if __name__ == "__main__":
    unittest.main()
