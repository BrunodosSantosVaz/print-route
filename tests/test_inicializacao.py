"""Testes de src/printroute/inicializacao.py: cria/remove de verdade uma Tarefa
Agendada (schtasks, tarefa #38 -- não mais a chave Run do Registro, que não inicia de
forma confiável um programa que precisa de elevação). Só faz sentido no Windows --
roda nos jobs "check" e "compat" da CI (windows-latest); no resto, pula."""
import sys
import unittest

import _caminho  # noqa: F401

_TEM_WINDOWS = sys.platform == "win32"

if _TEM_WINDOWS:
    from printroute import inicializacao

_CAMINHO_DE_TESTE = r"C:\PrintRouteTeste\PrintRoute.exe"


@unittest.skipUnless(_TEM_WINDOWS, "inicializacao.py só funciona no Windows (Registro)")
class HabilitarEDesabilitar(unittest.TestCase):
    def tearDown(self):
        inicializacao.desabilitar()

    def test_nao_habilitado_por_padrao(self):
        self.assertFalse(inicializacao.esta_habilitado())

    def test_habilitar_e_consultar(self):
        inicializacao.habilitar(_CAMINHO_DE_TESTE)
        self.assertTrue(inicializacao.esta_habilitado())

    def test_habilitar_duas_vezes_nao_falha(self):
        inicializacao.habilitar(_CAMINHO_DE_TESTE)
        inicializacao.habilitar(_CAMINHO_DE_TESTE)
        self.assertTrue(inicializacao.esta_habilitado())

    def test_desabilitar_remove(self):
        inicializacao.habilitar(_CAMINHO_DE_TESTE)
        inicializacao.desabilitar()
        self.assertFalse(inicializacao.esta_habilitado())

    def test_desabilitar_sem_estar_habilitado_nao_falha(self):
        inicializacao.desabilitar()
        self.assertFalse(inicializacao.esta_habilitado())


if __name__ == "__main__":
    unittest.main()
