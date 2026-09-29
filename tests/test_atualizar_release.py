"""atualizar_release.py: versão em src/printroute/version.py e seção da versão no CHANGELOG.md."""
import importlib.util
import json
import os
import tempfile
import unittest

import _caminho

_spec = importlib.util.spec_from_file_location(
    "atualizar_release", os.path.join(_caminho.RAIZ, ".github", "scripts", "atualizar_release.py"))
ar = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ar)

CHANGELOG = """# Changelog

Texto de abertura.

## [Não lançado]

## [0.1.0] - 2026-09-21

Primeira versão.

### Adicionado
- Esqueleto do programa
"""
ITENS = [
    {"numero": 12, "titulo": "Escolher a impressora de destino na hora", "tipo": "task"},
    {"numero": 9, "titulo": "Corrigir nome da impressora com acento", "tipo": "bug"},
    {"numero": 5, "titulo": "Reencaminhar para mais de uma impressora", "tipo": "task"},
]


class Changelog(unittest.TestCase):
    def test_insere_a_secao_abaixo_de_nao_lancado(self):
        novo = ar.atualizar_changelog(CHANGELOG, "0.2.0", "2026-10-01", ITENS)
        self.assertLess(novo.index("## [Não lançado]"), novo.index("## [0.2.0] - 2026-10-01"))
        self.assertLess(novo.index("## [0.2.0]"), novo.index("## [0.1.0]"))
        self.assertIn("### Adicionado\n- Reencaminhar para mais de uma impressora (#5)\n- Escolher a impressora de destino na hora (#12)\n", novo)
        self.assertIn("### Corrigido\n- Corrigir nome da impressora com acento (#9)\n", novo)
        self.assertIn("Primeira versão.", novo)  # o histórico anterior fica intacto

    def test_rodar_de_novo_substitui_sem_duplicar(self):
        um = ar.atualizar_changelog(CHANGELOG, "0.2.0", "2026-10-01", ITENS[:1])
        dois = ar.atualizar_changelog(um, "0.2.0", "2026-10-02", ITENS)
        self.assertEqual(dois.count("## [0.2.0]"), 1)
        self.assertIn("## [0.2.0] - 2026-10-02", dois)
        self.assertIn("(#9)", dois)
        self.assertEqual(ar.atualizar_changelog(dois, "0.2.0", "2026-10-02", ITENS), dois)  # idempotente

    def test_sem_bug_nao_cria_o_grupo_corrigido(self):
        novo = ar.atualizar_changelog(CHANGELOG, "0.2.0", "2026-10-01", ITENS[:1])
        self.assertNotIn("### Corrigido", novo)

    def test_sem_itens(self):
        self.assertIn("Sem mudanças listadas.", ar.atualizar_changelog(CHANGELOG, "0.2.0", "2026-10-01", []))

    def test_sem_marcador_insere_antes_da_primeira_versao(self):
        texto = "# Changelog\n\n## [0.1.0] - 2026-09-21\n\nx\n"
        novo = ar.atualizar_changelog(texto, "0.2.0", "2026-10-01", ITENS)
        self.assertLess(novo.index("## [0.2.0]"), novo.index("## [0.1.0]"))


class Versao(unittest.TestCase):
    def test_troca_so_a_linha_da_versao(self):
        novo = ar.atualizar_versao('"""doc"""\n\n__version__ = "0.1.0"\n', "0.2.0")
        self.assertIn('__version__ = "0.2.0"', novo)
        self.assertIn('"""doc"""', novo)

    def test_sem_linha_da_versao_falha(self):
        with self.assertRaises(SystemExit):
            ar.atualizar_versao("x = 1\n", "0.2.0")


class LinhaDeComando(unittest.TestCase):
    def test_atualiza_os_dois_arquivos_e_e_idempotente(self):
        with tempfile.TemporaryDirectory() as raiz:
            os.makedirs(os.path.join(raiz, "src", "printroute"))
            with open(os.path.join(raiz, "src", "printroute", "version.py"), "w", encoding="utf-8") as f:
                f.write('__version__ = "0.1.0"\n')
            with open(os.path.join(raiz, "CHANGELOG.md"), "w", encoding="utf-8") as f:
                f.write(CHANGELOG)
            with open(os.path.join(raiz, "itens.json"), "w", encoding="utf-8") as f:
                json.dump(ITENS, f)
            args = ["--versao", "0.2.0", "--data", "2026-10-01", "--itens", os.path.join(raiz, "itens.json"), "--raiz", raiz]
            self.assertEqual(ar.main(args), 0)
            with open(os.path.join(raiz, "src", "printroute", "version.py"), encoding="utf-8") as f:
                self.assertIn('"0.2.0"', f.read())
            caminho = os.path.join(raiz, "CHANGELOG.md")
            with open(caminho, encoding="utf-8") as f:
                antes = f.read()
            ar.main(args)
            with open(caminho, encoding="utf-8") as f:
                self.assertEqual(f.read(), antes)

    def test_sem_arquivo_de_versao_falha(self):
        with tempfile.TemporaryDirectory() as raiz:
            with open(os.path.join(raiz, "CHANGELOG.md"), "w", encoding="utf-8") as f:
                f.write(CHANGELOG)
            with open(os.path.join(raiz, "itens.json"), "w", encoding="utf-8") as f:
                json.dump(ITENS, f)
            with self.assertRaises(SystemExit):
                ar.main(["--versao", "0.2.0", "--data", "2026-10-01", "--itens", os.path.join(raiz, "itens.json"), "--raiz", raiz])

    def test_versao_invalida(self):
        with self.assertRaises(SystemExit):
            ar.main(["--versao", "v0.2", "--data", "x", "--itens", "nao-importa.json"])


if __name__ == "__main__":
    unittest.main()
