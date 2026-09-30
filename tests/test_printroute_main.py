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
class PedidoDeConfiguracoes(unittest.TestCase):
    """Bug real (achado testando o instalador de verdade): "Abrir configurações" abria a
    janela Tkinter direto na thread do pystray (não thread-safe), o que deixava a
    bandeja abrindo janela repetida e quebrava até o seletor. Agora só enfileira o
    pedido; quem abre é sempre a thread principal (ver __main__.py)."""

    def setUp(self):
        printroute_main._abrir_configuracoes_pendente()  # esvazia o que sobrou de outro teste
        printroute_main._parar.clear()

    def test_sem_pedido_na_fila_devolve_falso(self):
        self.assertFalse(printroute_main._abrir_configuracoes_pendente())

    def test_varios_cliques_viram_um_pedido_so(self):
        printroute_main._pedidos_de_ui.put_nowait(True)
        printroute_main._pedidos_de_ui.put_nowait(True)
        printroute_main._pedidos_de_ui.put_nowait(True)
        self.assertTrue(printroute_main._abrir_configuracoes_pendente())
        self.assertTrue(printroute_main._pedidos_de_ui.empty())
        self.assertFalse(printroute_main._abrir_configuracoes_pendente())  # já drenou

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
        printroute_main._pedidos_de_ui.put_nowait(True)
        self.addCleanup(printroute_main._parar.clear)
        printroute_main._observar_e_encaminhar(estado)
        abrir_configuracoes.assert_called_once_with(carregar.return_value)


if __name__ == "__main__":
    unittest.main()
