"""Testes de src/printroute/spooler/encaminhar.py.

`CapturarEEncaminhar` captura um trabalho de impressão de verdade (pela pasta de spool
do Windows) e confere o encaminhamento bruto para uma impressora de destino -- só faz
sentido no Windows (spooler de verdade), roda nos jobs "check" e "compat" da CI
(windows-latest); no resto, pula. `EncaminharParaConfiguracao` usa mock em vez de uma
impressora de verdade (só orquestração: quantas vezes e para quem `encaminhar_bytes` é
chamada) e roda em qualquer sistema, sem precisar do runner Windows."""
import sys
import threading
import time
import unittest
from unittest import mock

import _caminho  # noqa: F401
from printroute import configuracao
from printroute.spooler import encaminhar, gerenciar

_TEM_WINDOWS = sys.platform == "win32"

if _TEM_WINDOWS:
    import win32print


def _imprimir_bruto(nome_impressora: str, dados: bytes) -> None:
    hprinter = win32print.OpenPrinter(nome_impressora)
    try:
        win32print.StartDocPrinter(hprinter, 1, ("Teste PrintRoute", None, "RAW"))
        try:
            win32print.StartPagePrinter(hprinter)
            try:
                win32print.WritePrinter(hprinter, dados)
            finally:
                win32print.EndPagePrinter(hprinter)
        finally:
            win32print.EndDocPrinter(hprinter)
    finally:
        win32print.ClosePrinter(hprinter)


@unittest.skipUnless(_TEM_WINDOWS, "encaminhar.py só funciona no Windows (spooler de verdade)")
class CapturarEEncaminhar(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        gerenciar.instalar()

    @classmethod
    def tearDownClass(cls):
        gerenciar.desinstalar()

    def test_aguardar_trabalho_captura_os_bytes_enviados(self):
        dados = b"Teste do PrintRoute: " + b"x" * 500
        erro_na_thread = []

        def _imprimir_daqui_a_pouco():
            try:
                time.sleep(1)
                _imprimir_bruto(gerenciar.NOME_IMPRESSORA, dados)
            except Exception as erro:  # precisa chegar até a thread principal, não sumir na thread
                erro_na_thread.append(erro)

        thread = threading.Thread(target=_imprimir_daqui_a_pouco)
        thread.start()
        capturado = encaminhar.aguardar_trabalho(tempo_limite_s=20)
        thread.join(timeout=5)
        if erro_na_thread:
            raise erro_na_thread[0]
        if capturado is None:
            # Diagnóstico: o que realmente aconteceu no spooler, para não continuar
            # adivinhando às cegas numa próxima rodada de CI.
            hprinter = win32print.OpenPrinter(gerenciar.NOME_IMPRESSORA)
            try:
                trabalhos = win32print.EnumJobs(hprinter, 0, 999)
            finally:
                win32print.ClosePrinter(hprinter)
            try:
                arquivos = sorted(p.name for p in encaminhar.PASTA_SPOOL.iterdir())
            except OSError as erro:
                arquivos = f"<erro ao listar {encaminhar.PASTA_SPOOL}: {erro}>"
            porta = gerenciar._escolher_porta()
            driver = gerenciar._escolher_driver()
            self.fail(
                f"aguardar_trabalho devolveu None. Porta: {porta!r}, driver: {driver!r}. "
                f"Trabalhos na fila da PrintRoute: {trabalhos!r}. "
                f"Arquivos em {encaminhar.PASTA_SPOOL}: {arquivos!r}."
            )
        self.assertEqual(capturado, dados)

    def test_aguardar_trabalho_sem_nada_devolve_none(self):
        self.assertIsNone(encaminhar.aguardar_trabalho(tempo_limite_s=2))

    def test_encaminhar_bytes_nao_lanca_erro(self):
        encaminhar.encaminhar_bytes(gerenciar.NOME_IMPRESSORA, b"conteudo de teste do encaminhamento")


class EncaminharParaConfiguracao(unittest.TestCase):
    def test_encaminha_para_cada_impressora_o_numero_de_copias(self):
        config = configuracao.Configuracao(
            impressoras=[
                configuracao.ImpressoraDestino("HP LaserJet M404 (Escritório)", 2),
                configuracao.ImpressoraDestino("Epson L3250 (Recepção)", 1),
            ]
        )
        with mock.patch("printroute.spooler.encaminhar.encaminhar_bytes") as chamada:
            encaminhar.encaminhar_para_configuracao(b"dados do trabalho", config)
        self.assertEqual(
            chamada.call_args_list,
            [
                mock.call("HP LaserJet M404 (Escritório)", b"dados do trabalho"),
                mock.call("HP LaserJet M404 (Escritório)", b"dados do trabalho"),
                mock.call("Epson L3250 (Recepção)", b"dados do trabalho"),
            ],
        )

    def test_sem_impressoras_nao_chama_nada(self):
        with mock.patch("printroute.spooler.encaminhar.encaminhar_bytes") as chamada:
            encaminhar.encaminhar_para_configuracao(b"dados", configuracao.Configuracao())
        chamada.assert_not_called()


if __name__ == "__main__":
    unittest.main()
