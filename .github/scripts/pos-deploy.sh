#!/usr/bin/env bash
# Caminho MANUAL da publicacao (chamado por .github/workflows/pos-deploy.yml, via workflow_run do
# "Publicar release"): roda quando alguem mescla um PR na main por fora da acao "Publicar em producao"
# (tipicamente um hotfix/*, ou uma release mesclada na mao). A acao "Publicar em producao" ja faz tudo
# isso sozinha e nao passa por aqui.
#   1. identifica o PR que gerou o commit (release/* ou hotfix/*) e a versao;
#   2. release/*: encerra a sprint (issues, cartoes, epicos, milestone, branches das tarefas);
#      hotfix/*: fecha o bug e move o cartao para "Corrigido";
#   3. devolve a main para a develop (back-merge).
#
# Variaveis: SHA (commit da main), PROJETO_PLANEJAMENTO/EXECUCAO/BUGS, BRANCH_DEVELOP, BRANCH_MAIN,
# DRY_RUN=1 para simular.
set -euo pipefail

AQUI="$(cd "$(dirname "$0")" && pwd)"
SHA="${SHA:?}"
BUGS="${PROJETO_BUGS:?}"
MAIN="${BRANCH_MAIN:-main}"
R="$GITHUB_REPOSITORY"

run() { if [ "${DRY_RUN:-}" = 1 ]; then echo "[simulado] $*"; else "$@"; fi; }

pr=$(gh api "repos/$R/commits/$SHA/pulls" \
  --jq "[.[] | select(.merged_at != null and .base.ref == \"$MAIN\")][0] // {}")
head=$(jq -r '.head.ref // ""' <<<"$pr")
title=$(jq -r '.title // ""' <<<"$pr")
echo "PR de origem: '${head:-?}' ($title)"

versao=""
if   [[ "$head" =~ ^release/([0-9]+\.[0-9]+\.[0-9]+)$ ]]; then versao="${BASH_REMATCH[1]}"
elif [[ "$title" =~ ([0-9]+\.[0-9]+\.[0-9]+) ]];          then versao="${BASH_REMATCH[1]}"
elif bash "$(dirname "$0")/versao.sh" --arquivo >/dev/null 2>&1; then
  versao=$(bash "$(dirname "$0")/versao.sh")
fi
tag="v${versao:-?}"
[ -n "$versao" ] || echo "::warning::Versao nao identificada (branch, titulo ou arquivo de versao)."

if [[ "$head" =~ ^release/ ]] && [ -n "$versao" ]; then
  VERSAO="$versao" SIMULAR="$([ "${DRY_RUN:-}" = 1 ] && echo true || echo false)" bash "$AQUI/encerrar-sprint.sh"
elif [[ "$head" =~ ^hotfix/([0-9]+)- ]]; then
  n="${BASH_REMATCH[1]}"
  bash "$AQUI/projeto.sh" mover "$BUGS" "$n" "Corrigido"
  run gh issue close "$n" --reason completed --comment "Corrigido em produção na versão $tag (hotfix)."
fi

TAG="$tag" bash "$AQUI/backmerge.sh"
