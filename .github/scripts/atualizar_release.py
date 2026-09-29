#!/usr/bin/env python3
"""Atualiza a versao (src/printroute/version.py) e a secao da versao no CHANGELOG.md para uma release.

    atualizar_release.py --versao 0.2.0 --data 2026-10-01 --itens itens.json [--raiz .]

`itens.json`: lista de {"numero": 12, "titulo": "...", "tipo": "task" | "bug"}. Tarefas viram
"### Adicionado" e bugs "### Corrigido". Rodar de novo substitui a secao da mesma versao (nao
duplica). A secao entra logo abaixo de "## [Não lançado]".
"""
import argparse
import json
import os
import re
import sys


def secao_changelog(versao, data, itens):
    adicionados = [i for i in itens if i.get("tipo") != "bug"]
    corrigidos = [i for i in itens if i.get("tipo") == "bug"]
    linhas = [f"## [{versao}] - {data}", ""]
    for titulo, grupo in (("Adicionado", adicionados), ("Corrigido", corrigidos)):
        if grupo:
            linhas.append(f"### {titulo}")
            linhas += [f"- {i['titulo']} (#{i['numero']})" for i in sorted(grupo, key=lambda x: x["numero"])]
            linhas.append("")
    if not adicionados and not corrigidos:
        linhas += ["Sem mudanças listadas.", ""]
    return "\n".join(linhas)


def atualizar_changelog(texto, versao, data, itens):
    secao = secao_changelog(versao, data, itens)
    padrao = re.compile(rf"^## \[{re.escape(versao)}\][^\n]*\n.*?(?=^## \[|\Z)", re.S | re.M)
    if padrao.search(texto):
        return padrao.sub(lambda _m: secao + "\n", texto, count=1)
    marcador = re.search(r"^## \[Não lançado\][^\n]*\n", texto, re.M)
    if marcador:
        pos = marcador.end()
        resto = texto[pos:].lstrip("\n")
        return texto[:pos] + "\n" + secao + "\n" + resto
    primeira = re.search(r"^## \[", texto, re.M)
    if primeira:
        return texto[:primeira.start()] + secao + "\n" + texto[primeira.start():]
    return texto.rstrip("\n") + "\n\n" + secao + "\n"


def atualizar_versao(texto, versao):
    # sem ancora de fim de linha: funciona com LF e CRLF
    novo, n = re.subn(r'^__version__ = "[^"]*"', f'__version__ = "{versao}"', texto, flags=re.M)
    if n != 1:
        raise SystemExit("arquivo de versao: linha __version__ nao encontrada")
    return novo


ARQUIVO_DE_VERSAO = os.path.join("src", "printroute", "version.py")


def arquivo_de_versao(raiz):
    """Caminho (relativo a raiz) do arquivo de versao. Mesma regra do versao.sh."""
    if os.path.isfile(os.path.join(raiz, ARQUIVO_DE_VERSAO)):
        return ARQUIVO_DE_VERSAO
    raise SystemExit(f"arquivo de versao nao encontrado ({ARQUIVO_DE_VERSAO})")


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--versao", required=True)
    p.add_argument("--data", required=True)
    p.add_argument("--itens", required=True, help="arquivo JSON com a lista de itens")
    p.add_argument("--raiz", default=".")
    a = p.parse_args(argv)
    if not re.fullmatch(r"\d+\.\d+\.\d+", a.versao):
        raise SystemExit(f"versao invalida: {a.versao}")
    with open(a.itens, encoding="utf-8") as f:
        itens = json.load(f)
    alterados = []
    for caminho, funcao in ((arquivo_de_versao(a.raiz), lambda t: atualizar_versao(t, a.versao)),
                            ("CHANGELOG.md", lambda t: atualizar_changelog(t, a.versao, a.data, itens))):
        completo = os.path.join(a.raiz, caminho)
        with open(completo, encoding="utf-8", newline="") as f:
            antigo = f.read()
        crlf = "\r\n" in antigo                      # preserva o fim de linha do arquivo
        novo = funcao(antigo.replace("\r\n", "\n"))
        if crlf:
            novo = novo.replace("\n", "\r\n")
        if novo != antigo:
            with open(completo, "w", encoding="utf-8", newline="") as f:
                f.write(novo)
            alterados.append(caminho)
    print("alterados:", ", ".join(alterados) if alterados else "nada")
    return 0


if __name__ == "__main__":
    sys.exit(main())
