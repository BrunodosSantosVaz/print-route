"""Testes de src/printroute/selecao.py: lógica do seletor de impressora na hora, sem
interface gráfica -- roda em qualquer sistema."""
import unittest

import _caminho  # noqa: F401
from printroute import configuracao, selecao


class ImpressorasCandidatas(unittest.TestCase):
    def test_lista_os_nomes_na_ordem_configurada(self):
        config = configuracao.Configuracao(
            impressoras=[configuracao.ImpressoraDestino("B"), configuracao.ImpressoraDestino("A")]
        )
        self.assertEqual(selecao.impressoras_candidatas(config), ["B", "A"])

    def test_vazia_sem_impressoras(self):
        self.assertEqual(selecao.impressoras_candidatas(configuracao.Configuracao()), [])


class EscolhaPadrao(unittest.TestCase):
    def test_primeira_candidata_com_copias_da_configuracao(self):
        config = configuracao.Configuracao(
            impressoras=[configuracao.ImpressoraDestino("A"), configuracao.ImpressoraDestino("B")],
            copias_no_seletor=3,
        )
        self.assertEqual(selecao.escolha_padrao(config), selecao.EscolhaDoUsuario("A", 3))

    def test_sem_candidatas_levanta_erro(self):
        with self.assertRaises(selecao.SemImpressoraCandidataError):
            selecao.escolha_padrao(configuracao.Configuracao())


class ValidarEscolha(unittest.TestCase):
    def setUp(self):
        self.config = configuracao.Configuracao(impressoras=[configuracao.ImpressoraDestino("A")])

    def test_escolha_valida_nao_levanta(self):
        selecao.validar_escolha(selecao.EscolhaDoUsuario("A", 1), self.config)

    def test_impressora_fora_da_lista_levanta(self):
        with self.assertRaises(ValueError):
            selecao.validar_escolha(selecao.EscolhaDoUsuario("Outra", 1), self.config)

    def test_copias_menor_que_um_levanta(self):
        with self.assertRaises(ValueError):
            selecao.validar_escolha(selecao.EscolhaDoUsuario("A", 0), self.config)


if __name__ == "__main__":
    unittest.main()
