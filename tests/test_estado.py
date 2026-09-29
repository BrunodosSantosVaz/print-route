"""Testes de src/printroute/estado.py. Sem dependência do Windows: roda em qualquer
sistema."""
import unittest

import _caminho  # noqa: F401
from printroute.estado import EstadoApp


class Alternar(unittest.TestCase):
    def test_comeca_ativo(self):
        self.assertTrue(EstadoApp().ativo)

    def test_alternar_inverte(self):
        estado = EstadoApp()
        estado.alternar()
        self.assertFalse(estado.ativo)
        estado.alternar()
        self.assertTrue(estado.ativo)


if __name__ == "__main__":
    unittest.main()
