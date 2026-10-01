"""Testes de src/printroute/__main__.py: só o modo `--desinstalar` (tarefa #12), que é
lógica pura (chama gerenciar.desinstalar() e inicializacao.desabilitar(), sem UI). O
resto do módulo (bandeja, seletor) não tem teste automatizado (ver AGENTS.md) -- e o
próprio import do módulo exige Tkinter, só garantido no Windows (ver README), por isso
esses testes também só rodam lá."""
import sys
import unittest
from unittest import mock

import _caminho  # noqa: F401

_TEM_WINDOWS = sys.platform == "win32"

if _TEM_WINDOWS:
    from printroute import __main__ as printroute_main


@unittest.skipUnless(_TEM_WINDOWS, "importa a UI (Tkinter/pystray), só garantida no Windows")
class Desinstalar(unittest.TestCase):
    @mock.patch("printroute.__main__.inicializacao")
    @mock.patch("printroute.__main__.gerenciar")
    def test_desinstalar_remove_impressora_e_inicio_automatico(self, gerenciar, inicializacao):
        printroute_main._desinstalar()
        gerenciar.desinstalar.assert_called_once_with()
        inicializacao.desabilitar.assert_called_once_with()

    @mock.patch("printroute.__main__._desinstalar")
    @mock.patch("printroute.__main__.gerenciar")
    @mock.patch("printroute.__main__.bandeja")
    def test_main_com_flag_so_desinstala_sem_abrir_a_bandeja(self, bandeja, gerenciar, _desinstalar):
        with mock.patch.object(sys, "argv", ["printroute", "--desinstalar"]):
            printroute_main.main()
        _desinstalar.assert_called_once_with()
        gerenciar.instalar.assert_not_called()
        bandeja.criar_icone.assert_not_called()


@unittest.skipUnless(_TEM_WINDOWS, "importa a UI (Tkinter/pystray), só garantida no Windows")
class PedidosDeUi(unittest.TestCase):
    """Bug real (achado testando o instalador de verdade): "Abrir configurações" abria a
    janela Tkinter direto na thread do pystray (não thread-safe), o que deixava a
    bandeja abrindo janela repetida e quebrava até o seletor. Agora só enfileira o
    pedido; quem abre é sempre a thread principal (ver __main__.py). "Sobre o
    PrintRoute" (tarefa #40) virou janela de verdade e passou a seguir a mesma regra."""

    def setUp(self):
        printroute_main._pedidos_de_ui_pendentes()  # esvazia o que sobrou de outro teste
        printroute_main._parar.clear()

    def test_sem_pedido_na_fila_devolve_vazio(self):
        self.assertEqual(printroute_main._pedidos_de_ui_pendentes(), set())

    def test_varios_cliques_no_mesmo_item_viram_um_pedido_so(self):
        printroute_main._pedidos_de_ui.put_nowait("configuracoes")
        printroute_main._pedidos_de_ui.put_nowait("configuracoes")
        printroute_main._pedidos_de_ui.put_nowait("configuracoes")
        self.assertEqual(printroute_main._pedidos_de_ui_pendentes(), {"configuracoes"})
        self.assertTrue(printroute_main._pedidos_de_ui.empty())
        self.assertEqual(printroute_main._pedidos_de_ui_pendentes(), set())  # já drenou

    def test_pedidos_diferentes_ficam_distintos(self):
        printroute_main._pedidos_de_ui.put_nowait("configuracoes")
        printroute_main._pedidos_de_ui.put_nowait("sobre")
        self.assertEqual(printroute_main._pedidos_de_ui_pendentes(), {"configuracoes", "sobre"})

    @mock.patch("printroute.__main__.abrir_configuracoes")
    @mock.patch("printroute.__main__.carregar")
    @mock.patch("printroute.__main__.encaminhar")
    @mock.patch("printroute.__main__.gerenciar")
    def test_pedido_pendente_abre_configuracoes_no_laco_principal(
        self, gerenciar, encaminhar, carregar, abrir_configuracoes
    ):
        estado = mock.Mock(ativo=False)

        def _aguardar_uma_vez(*_args, **_kwargs):
            printroute_main._parar.set()  # só uma volta do laço
            return None

        encaminhar.aguardar_trabalho.side_effect = _aguardar_uma_vez
        printroute_main._pedidos_de_ui.put_nowait("configuracoes")
        self.addCleanup(printroute_main._parar.clear)
        printroute_main._observar_e_encaminhar(estado)
        abrir_configuracoes.assert_called_once_with(carregar.return_value)

    @mock.patch("printroute.__main__.abrir_sobre")
    @mock.patch("printroute.__main__.carregar")
    @mock.patch("printroute.__main__.encaminhar")
    @mock.patch("printroute.__main__.gerenciar")
    def test_pedido_pendente_abre_sobre_no_laco_principal(self, gerenciar, encaminhar, carregar, abrir_sobre):
        estado = mock.Mock(ativo=False)

        def _aguardar_uma_vez(*_args, **_kwargs):
            printroute_main._parar.set()  # só uma volta do laço
            return None

        encaminhar.aguardar_trabalho.side_effect = _aguardar_uma_vez
        printroute_main._pedidos_de_ui.put_nowait("sobre")
        self.addCleanup(printroute_main._parar.clear)
        printroute_main._observar_e_encaminhar(estado)
        abrir_sobre.assert_called_once_with()


@unittest.skipUnless(_TEM_WINDOWS, "importa a UI (Tkinter/pystray), só garantida no Windows")
class ResilienciaDoLaco(unittest.TestCase):
    """Bug real, achado ao vivo: um config.json com BOM derrubava o laço inteiro (e o
    processo junto, sem nenhum vestígio -- o .exe é --windowed, sem console). Um erro
    num trabalho/configuração não pode tirar o PrintRoute do ar."""

    def setUp(self):
        printroute_main._pedidos_de_ui_pendentes()
        printroute_main._parar.clear()
        self.addCleanup(printroute_main._parar.clear)

    @mock.patch("printroute.__main__._registrar_erro")
    @mock.patch("printroute.__main__.carregar")
    @mock.patch("printroute.__main__.encaminhar")
    @mock.patch("printroute.__main__.gerenciar")
    @mock.patch("printroute.__main__.time.sleep")  # a pausa é real (1s); não vale a pena no teste
    def test_erro_no_laco_e_registrado_e_o_laco_continua(self, _sleep, gerenciar, encaminhar, carregar, _registrar_erro):
        estado = mock.Mock(ativo=True)
        voltas = []

        def _aguardar(*_args, **_kwargs):
            voltas.append(1)
            if len(voltas) >= 2:
                printroute_main._parar.set()
            return b"dados"

        encaminhar.aguardar_trabalho.side_effect = _aguardar
        carregar.side_effect = ValueError("config.json quebrado")

        printroute_main._observar_e_encaminhar(estado)  # não deve propagar o ValueError

        self.assertEqual(len(voltas), 2)  # o erro na 1a volta não impediu a 2a
        self.assertEqual(_registrar_erro.call_count, 2)
        # Achado ao vivo: sem a pausa, um erro que persiste martela o disco (erro.log
        # cresceu 282 KB em ~3s numa corrida real) -- confere que ela sempre acontece.
        self.assertEqual(_sleep.call_count, 2)
        _sleep.assert_called_with(printroute_main.PAUSA_APOS_ERRO_S)


if __name__ == "__main__":
    unittest.main()
