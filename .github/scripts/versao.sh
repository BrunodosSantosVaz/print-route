#!/usr/bin/env bash
# Ponto unico para achar a versao do PrintRoute (SemVer, "__version__" em src/printroute/version.py).
# Uso: versao.sh            imprime a versao (ex.: 0.1.0)
#      versao.sh --arquivo  imprime o caminho do arquivo de versao
# Roda na raiz do repositorio (ou de uma copia/worktree dele). Sem arquivo ou sem __version__: erro.
set -euo pipefail

arquivo=src/printroute/version.py
[ -f "$arquivo" ] || { echo "::error::Arquivo de versao nao encontrado ($arquivo)." >&2; exit 1; }

if [ "${1:-}" = --arquivo ]; then echo "$arquivo"; exit 0; fi
versao=$(sed -n 's/^__version__ = "\(.*\)"$/\1/p' "$arquivo")
[ -n "$versao" ] || { echo "::error::Nao consegui ler __version__ em $arquivo." >&2; exit 1; }
echo "$versao"
