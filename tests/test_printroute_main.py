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


if __name__ == "__main__":
    unittest.main()
