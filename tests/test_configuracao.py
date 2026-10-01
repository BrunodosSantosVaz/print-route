"""Testes de src/printroute/configuracao.py. Sem dependência do Windows: roda em
qualquer sistema, sempre passando um caminho próprio (nunca o CAMINHO_PADRAO, que é do
Windows) para não tocar em nada fora da pasta temporária do teste."""
import pathlib
import tempfile
import unittest

import _caminho  # noqa: F401
from printroute import configuracao


class CarregarESalvar(unittest.TestCase):
    def _caminho_temp(self) -> pathlib.Path:
        pasta = tempfile.TemporaryDirectory()
        self.addCleanup(pasta.cleanup)
        return pathlib.Path(pasta.name) / "config.json"

    def test_carregar_sem_arquivo_devolve_padrao(self):
        lido = configuracao.carregar(self._caminho_temp())
        self.assertEqual(lido.modo, configuracao.MODO_FIXO)
        self.assertEqual(lido.impressoras, [])
        self.assertEqual(lido.copias_no_seletor, 1)

    def test_carregar_tolera_bom_utf8(self):
        # Bug real, achado ao vivo: Notepad ("UTF-8") e o PowerShell
        # (Set-Content -Encoding UTF8) gravam um BOM no início do arquivo -- "utf-8"
        # puro não tolera isso (json.JSONDecodeError), derrubando o laço de captura
        # inteiro.
        caminho = self._caminho_temp()
        caminho.write_bytes(b"\xef\xbb\xbf" + b'{"modo": "fixo", "impressoras": [], "copias_no_seletor": 1}')
        lido = configuracao.carregar(caminho)
        self.assertEqual(lido, configuracao.Configuracao())

    def test_salvar_e_carregar_preserva_os_dados(self):
        caminho = self._caminho_temp()
        original = configuracao.Configuracao(
            modo=configuracao.MODO_FIXO,
            impressoras=[
                configuracao.ImpressoraDestino("HP LaserJet M404 (Escritório)", 2),
                configuracao.ImpressoraDestino("Epson L3250 (Recepção)", 1),
            ],
            copias_no_seletor=3,
        )
        configuracao.salvar(original, caminho)
        lido = configuracao.carregar(caminho)
        self.assertEqual(lido, original)

    def test_salvar_cria_a_pasta_se_nao_existir(self):
        caminho = self._caminho_temp().parent / "subpasta" / "config.json"
        configuracao.salvar(configuracao.Configuracao(), caminho)
        self.assertTrue(caminho.exists())

    def test_salvar_de_novo_sobrescreve(self):
        caminho = self._caminho_temp()
        configuracao.salvar(configuracao.Configuracao(modo=configuracao.MODO_FIXO), caminho)
        configuracao.salvar(configuracao.Configuracao(modo=configuracao.MODO_PERGUNTAR), caminho)
        self.assertEqual(configuracao.carregar(caminho).modo, configuracao.MODO_PERGUNTAR)

    def test_arquivo_e_json_legivel(self):
        caminho = self._caminho_temp()
        configuracao.salvar(
            configuracao.Configuracao(impressoras=[configuracao.ImpressoraDestino("X", 1)]), caminho
        )
        self.assertIn('"impressoras"', caminho.read_text(encoding="utf-8"))


class Validacao(unittest.TestCase):
    def test_modo_invalido_recusa(self):
        with self.assertRaises(ValueError):
            configuracao.Configuracao(modo="modo-que-nao-existe")

    def test_copias_no_seletor_menor_que_um_recusa(self):
        with self.assertRaises(ValueError):
            configuracao.Configuracao(copias_no_seletor=0)

    def test_copias_da_impressora_menor_que_um_recusa(self):
        with self.assertRaises(ValueError):
            configuracao.ImpressoraDestino("X", 0)

    def test_modos_validos_aceitos(self):
        configuracao.Configuracao(modo=configuracao.MODO_FIXO)
        configuracao.Configuracao(modo=configuracao.MODO_PERGUNTAR)


if __name__ == "__main__":
    unittest.main()
