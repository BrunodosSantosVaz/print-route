"""Testes de src/printroute/spooler/encaminhar.py.

`CapturarEEncaminhar` captura um trabalho de impressão de verdade (pela pasta de spool
do Windows) e confere o encaminhamento bruto para uma impressora de destino -- só faz
sentido no Windows (spooler de verdade), roda nos jobs "check" e "compat" da CI
(windows-latest); no resto, pula. `EncaminharParaConfiguracao` usa mock em vez de uma
impressora de verdade (só orquestração: quantas vezes e para quem `encaminhar_bytes` é
chamada) e roda em qualquer sistema, sem precisar do runner Windows."""
import os
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

import _caminho  # noqa: F401
from printroute import configuracao, selecao
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
        capturado = encaminhar.aguardar_trabalho(gerenciar.NOME_IMPRESSORA, tempo_limite_s=20)
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
        self.assertIsNone(encaminhar.aguardar_trabalho(gerenciar.NOME_IMPRESSORA, tempo_limite_s=2))

    def test_encaminhar_bytes_nao_lanca_erro(self):
        encaminhar.encaminhar_bytes(gerenciar.NOME_IMPRESSORA, b"conteudo de teste do encaminhamento")


class DetectarEEscolherCaminho(unittest.TestCase):
    """Bug real, achado ao vivo (tarefa #34): o driver "Microsoft Print To PDF" (e
    outros v4/XPS) spoola um pacote XPS (ZIP), não bytes brutos -- mandar isso como
    RAW pra outra impressora corrompe o documento. `_e_xps`/`encaminhar_bytes`
    decidem qual caminho usar; roda em qualquer sistema (lógica pura ou mocks, sem
    precisar do runner Windows)."""

    def test_pacote_xps_e_detectado_pela_assinatura_zip(self):
        self.assertTrue(encaminhar._e_xps(b"PK\x03\x04" + b"resto do pacote"))

    def test_texto_puro_nao_e_detectado_como_xps(self):
        self.assertFalse(encaminhar._e_xps(b"Teste do PrintRoute: xxxx"))

    def test_vazio_nao_e_detectado_como_xps(self):
        self.assertFalse(encaminhar._e_xps(b""))

    @mock.patch("printroute.spooler.encaminhar._encaminhar_raw")
    @mock.patch("printroute.spooler.encaminhar._encaminhar_xps")
    def test_pacote_xps_usa_o_caminho_do_ghostscript(self, xps, raw):
        encaminhar.encaminhar_bytes("Impressora", b"PK\x03\x04conteudo")
        xps.assert_called_once_with("Impressora", b"PK\x03\x04conteudo")
        raw.assert_not_called()

    @mock.patch("printroute.spooler.encaminhar._encaminhar_raw")
    @mock.patch("printroute.spooler.encaminhar._encaminhar_xps")
    def test_texto_puro_usa_o_caminho_bruto(self, xps, raw):
        encaminhar.encaminhar_bytes("Impressora", b"so texto", nome_trabalho="Job")
        raw.assert_called_once_with("Impressora", b"so texto", "Job")
        xps.assert_not_called()


class LocalizarGhostscript(unittest.TestCase):
    def test_variavel_de_ambiente_tem_prioridade(self):
        with mock.patch.dict("os.environ", {"PRINTROUTE_GXPS": "/caminho/customizado/gxps.exe"}):
            self.assertEqual(encaminhar._localizar_gxps(), "/caminho/customizado/gxps.exe")

    def test_sem_variavel_usa_a_pasta_do_executavel(self):
        # os.path.dirname/join só entendem separador do sistema onde o teste roda (no
        # Windows de verdade seria "\\", aqui pode ser "/") -- usa o separador certo
        # dos dois lados da comparação em vez de fixar um dos dois.
        pasta = os.path.join("pasta", "do", "executavel")
        with (
            mock.patch.dict("os.environ", {}, clear=True),
            mock.patch("sys.executable", os.path.join(pasta, "PrintRoute.exe")),
        ):
            caminho = encaminhar._localizar_gxps()
        self.assertEqual(caminho, os.path.join(pasta, "ghostxps", "gxpswin64.exe"))


class EncaminharXps(unittest.TestCase):
    """Mocka subprocess.run: confere o comando montado, sem precisar do Ghostscript
    de verdade nem do runner Windows."""

    @mock.patch("printroute.spooler.encaminhar._localizar_gxps", return_value="C:\\gxps\\gxpswin64.exe")
    @mock.patch("printroute.spooler.encaminhar.subprocess.run")
    def test_monta_o_comando_certo(self, executar, _localizar):
        encaminhar._encaminhar_xps("Impressora Real", b"PK\x03\x04conteudo xps")
        executar.assert_called_once()
        cmd = executar.call_args.args[0]
        self.assertEqual(cmd[0], "C:\\gxps\\gxpswin64.exe")
        self.assertIn("-sDEVICE=mswinpr2", cmd)
        self.assertIn("-sOutputFile=%printer%Impressora Real", cmd)
        self.assertTrue(executar.call_args.kwargs.get("check"))
        # Bug real, achado ao vivo: uma impressora de destino que precisa de interação
        # (ex.: "Microsoft Print to PDF" sem sessão pra responder o diálogo) nunca
        # completa -- sem limite, travaria o laço de captura inteiro para sempre.
        self.assertEqual(executar.call_args.kwargs.get("timeout"), encaminhar.TEMPO_LIMITE_GHOSTSCRIPT_S)
        # Bug real, achado ao vivo (tarefa #36): sem isso, a janela de console do
        # gxpswin64.exe (programa de linha de comando) aparecia na tela a cada
        # trabalho, mesmo o PrintRoute sendo --windowed.
        self.assertIn("creationflags", executar.call_args.kwargs)

    @mock.patch("printroute.spooler.encaminhar._localizar_gxps", return_value="C:\\gxps\\gxpswin64.exe")
    @mock.patch("printroute.spooler.encaminhar.subprocess.run")
    def test_apaga_o_arquivo_temporario_mesmo_se_der_erro(self, executar, _localizar):
        executar.side_effect = RuntimeError("falhou")
        caminhos_escritos = []
        original_tmp = tempfile.NamedTemporaryFile

        def _tmp_espiao(*args, **kwargs):
            arquivo = original_tmp(*args, **kwargs)
            caminhos_escritos.append(arquivo.name)
            return arquivo

        with (
            mock.patch("printroute.spooler.encaminhar.tempfile.NamedTemporaryFile", side_effect=_tmp_espiao),
            self.assertRaises(RuntimeError),
        ):
            encaminhar._encaminhar_xps("Impressora", b"PK\x03\x04conteudo")
        self.assertFalse(os.path.exists(caminhos_escritos[0]))


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


class EncaminharEscolha(unittest.TestCase):
    def test_encaminha_o_numero_de_copias_da_escolha(self):
        escolha = selecao.EscolhaDoUsuario(impressora="Epson L3250 (Recepção)", copias=2)
        with mock.patch("printroute.spooler.encaminhar.encaminhar_bytes") as chamada:
            encaminhar.encaminhar_escolha(b"dados do trabalho", escolha)
        self.assertEqual(
            chamada.call_args_list,
            [
                mock.call("Epson L3250 (Recepção)", b"dados do trabalho"),
                mock.call("Epson L3250 (Recepção)", b"dados do trabalho"),
            ],
        )

    def test_uma_copia_chama_uma_vez(self):
        escolha = selecao.EscolhaDoUsuario(impressora="HP", copias=1)
        with mock.patch("printroute.spooler.encaminhar.encaminhar_bytes") as chamada:
            encaminhar.encaminhar_escolha(b"dados", escolha)
        chamada.assert_called_once_with("HP", b"dados")


if __name__ == "__main__":
    unittest.main()
