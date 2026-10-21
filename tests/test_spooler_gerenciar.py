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


class ImpressoraExiste(unittest.TestCase):
    """Bug real, achado ao vivo em produção (tarefa #43): `Get-Printer -Name X`
    (filtrada) não é confiável -- às vezes devolve vazio mesmo com a impressora
    cadastrada. Virou "listar tudo e conferir no Python", mesmo padrão de
    `_escolher_porta`/`_escolher_driver`."""

    @mock.patch("printroute.spooler.gerenciar._powershell")
    def test_na_lista_e_true(self, _powershell):
        _powershell.return_value = '["Microsoft Print to PDF","PrintRoute"]'
        self.assertTrue(gerenciar.impressora_existe())

    @mock.patch("printroute.spooler.gerenciar._powershell")
    def test_fora_da_lista_e_false(self, _powershell):
        _powershell.return_value = '["Microsoft Print to PDF"]'
        self.assertFalse(gerenciar.impressora_existe())

    @mock.patch("printroute.spooler.gerenciar._powershell")
    def test_uma_so_impressora_no_sistema(self, _powershell):
        # Get-Printer com um resultado só devolve string, não lista (ConvertTo-Json).
        _powershell.return_value = '"PrintRoute"'
        self.assertTrue(gerenciar.impressora_existe())

    @mock.patch("printroute.spooler.gerenciar._powershell")
    def test_sem_impressora_nenhuma_no_sistema(self, _powershell):
        _powershell.return_value = ""
        self.assertFalse(gerenciar.impressora_existe())


class Instalar(unittest.TestCase):
    """Bug real, achado ao vivo em produção (tarefa #43): a condição de corrida de
    `impressora_existe()` fazia `Add-Printer` ser chamado numa impressora que já
    existia, e o cmdlet falhava -- derrubando o app inteiro antes até da bandeja
    aparecer. `instalar()` agora tolera esse erro específico, conferindo o estado de
    verdade depois (não só confiando na checagem prévia)."""

    @mock.patch("printroute.spooler.gerenciar._escolher_porta")
    @mock.patch("printroute.spooler.gerenciar._escolher_driver")
    @mock.patch("printroute.spooler.gerenciar._powershell")
    def test_ja_existe_nao_chama_add_printer(self, _powershell, _driver, _porta):
        _powershell.return_value = '"PrintRoute"'  # impressora_existe() -> True
        gerenciar.instalar()
        _powershell.assert_called_once()  # só a checagem, nenhum Add-Printer
        _driver.assert_not_called()
        _porta.assert_not_called()

    @mock.patch("printroute.spooler.gerenciar._escolher_porta", return_value="nul:")
    @mock.patch("printroute.spooler.gerenciar._escolher_driver", return_value="Microsoft Print to PDF")
    @mock.patch("printroute.spooler.gerenciar._powershell")
    def test_add_printer_falha_mas_impressora_ja_existe_nao_propaga(self, _powershell, _driver, _porta):
        respostas = iter(["", gerenciar._MARCADOR_DE_ERRO + " A impressora especificada já existe.", '"PrintRoute"'])

        def _powershell_falso(_comando):
            resposta = next(respostas)
            if resposta.startswith(gerenciar._MARCADOR_DE_ERRO):
                raise gerenciar.ErroDoPowerShell(resposta[len(gerenciar._MARCADOR_DE_ERRO) :].strip())
            return resposta

        _powershell.side_effect = _powershell_falso
        gerenciar.instalar()  # não deve levantar ErroDoPowerShell

    @mock.patch("printroute.spooler.gerenciar._escolher_porta", return_value="nul:")
    @mock.patch("printroute.spooler.gerenciar._escolher_driver", return_value="Microsoft Print to PDF")
    @mock.patch("printroute.spooler.gerenciar._powershell")
    def test_add_printer_falha_de_verdade_propaga(self, _powershell, _driver, _porta):
        respostas = iter(["", gerenciar._MARCADOR_DE_ERRO + " Driver nao encontrado.", ""])

        def _powershell_falso(_comando):
            resposta = next(respostas)
            if resposta.startswith(gerenciar._MARCADOR_DE_ERRO):
                raise gerenciar.ErroDoPowerShell(resposta[len(gerenciar._MARCADOR_DE_ERRO) :].strip())
            return resposta

        _powershell.side_effect = _powershell_falso
        with self.assertRaises(gerenciar.ErroDoPowerShell):
            gerenciar.instalar()


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
