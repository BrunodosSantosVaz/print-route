#!/usr/bin/env bash
# Mescla, UMA POR UMA e com commit de merge (--no-ff), varias referencias em uma branch de destino.
# Uso: mesclar.sh DESTINO BASE "rotulo=refspec" ["rotulo=refspec" ...]
#   DESTINO : branch que recebe (se nao existe no origin, e criada a partir de origin/BASE)
#   BASE    : branch de partida quando DESTINO ainda nao existe
#   refspec : o que buscar no origin (ex.: refs/pull/12/head ou refs/heads/release/0.2.0)
# Saida (uma linha por item):  MESCLADO <rotulo>  |  JA_INCLUIDO <rotulo>
# Se um merge tem conflito: aborta, imprime "CONFLITO <rotulo>" e sai com codigo 3, deixando a
# branch local exatamente como estava antes do item (nada e enviado ao origin por este script).
set -euo pipefail

destino="${1:?destino}"; base="${2:?base}"; shift 2
git config user.name  >/dev/null 2>&1 || git config user.name  "github-actions[bot]"
git config user.email >/dev/null 2>&1 || git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

git fetch -q origin "+refs/heads/${base}:refs/remotes/origin/${base}"
if git fetch -q origin "+refs/heads/${destino}:refs/remotes/origin/${destino}" 2>/dev/null; then
  git checkout -q -B "$destino" "origin/${destino}"
else
  git checkout -q -B "$destino" "origin/${base}"
fi

for item in "$@"; do
  rotulo="${item%%=*}"; refspec="${item#*=}"
  git fetch -q origin "$refspec"
  sha=$(git rev-parse FETCH_HEAD)
  if git merge-base --is-ancestor "$sha" HEAD; then
    echo "JA_INCLUIDO $rotulo"; continue
  fi
  if git merge --no-ff --no-edit -m "Merge $rotulo" "$sha" >/dev/null 2>&1; then
    echo "MESCLADO $rotulo"
  else
    git merge --abort >/dev/null 2>&1 || true
    echo "CONFLITO $rotulo"
    exit 3
  fi
done
