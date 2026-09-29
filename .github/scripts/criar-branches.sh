#!/usr/bin/env bash
# "Criar branches das tarefas": para cada tarefa em "A fazer" (painel Execucao) e cada bug em
# "Novo" (painel Bugs) que ja esta em um milestone (isto e, entrou em uma sprint), cria a branch
# feature/<n>-<slug> (bugfix/<n>-<slug> para bug) a partir da develop e move o cartao para
# "Feature" ("Em correcao" para bug). Issues sem milestone (backlog) sao ignoradas, exceto as
# `sem-executavel` que estao numa Sprint (campo Iteration): sprint sem versao, sem milestone.
# Cartao "Reprovado" (recusado na homologacao) tambem entra: a branch e recriada a partir da develop e
# o cartao volta para "Code" (tarefa) / "Em correcao" (bug), para passar de novo pela mesma esteira.
# Idempotente: se a branch ja existe, so garante o cartao.
#
# Variaveis: PROJETO_EXECUCAO, PROJETO_BUGS, VERSAO (opcional: so o milestone dessa versao),
# SPRINT (opcional: so as tarefas sem-executavel sem milestone dessa Sprint; padrao qualquer Sprint),
# SIMULAR=true, BRANCH_DEVELOP (develop).
set -euo pipefail

AQUI="$(cd "$(dirname "$0")" && pwd)"
EXEC="${PROJETO_EXECUCAO:?}"; BUGS="${PROJETO_BUGS:?}"
R="$GITHUB_REPOSITORY"
DEVELOP="${BRANCH_DEVELOP:-develop}"
FILTRO=""; [ -z "${VERSAO:-}" ] || FILTRO="v${VERSAO#v}"
SIMULAR="${SIMULAR:-false}"
[ "$SIMULAR" = true ] && export DRY_RUN=1
run() { if [ "$SIMULAR" = true ]; then echo "[simulado] $*"; else "$@"; fi; }
projeto() { bash "$AQUI/projeto.sh" "$@"; }

criadas=0
# processar <painel> <prefixo da branch> <coluna de origem> <coluna de destino>
processar() {
  local painel="$1" prefixo="$2" de="$3" para="$4" n estado milestone sem_exe titulo slug branch sha sprint
  for n in $(projeto cartoes "$painel" "$de"); do
    IFS=$'\t' read -r estado milestone sem_exe titulo <<<"$(gh api "repos/$R/issues/$n" \
      --jq '[.state, (.milestone.title // "-"), ([.labels[].name] | index("sem-executavel") != null), .title] | @tsv')"
    [ "$estado" = open ] || continue
    if [ "$milestone" = "-" ]; then
      # sprint sem versao: tarefa sem-executavel sem milestone, mas numa Sprint
      sprint=""; [ "$sem_exe" != true ] || sprint=$(projeto sprint-de "$painel" "$n" 2>/dev/null || true)
      if [ -z "$sprint" ]; then echo "#$n sem milestone (backlog): ignorada."; continue; fi
      if [ -n "${SPRINT:-}" ] && [ "$sprint" != "$SPRINT" ]; then continue; fi
      echo "#$n sem-executavel na $sprint (sem versao)."
    elif [ -n "$FILTRO" ] && [ "$milestone" != "$FILTRO" ]; then continue; fi
    slug=$(bash "$AQUI/slug.sh" "$titulo"); branch="$prefixo/$n-$slug"
    if gh api "repos/$R/git/ref/heads/$branch" >/dev/null 2>&1; then
      echo "#$n: branch $branch ja existe."
    else
      sha=$(gh api "repos/$R/git/ref/heads/$DEVELOP" --jq '.object.sha')
      run gh api --silent -X POST "repos/$R/git/refs" -f ref="refs/heads/$branch" -f sha="$sha"
      run gh issue comment "$n" --repo "$R" --body "Branch criada a partir da \`$DEVELOP\`: \`$branch\`. Desenvolva nela e abra o PR para a \`$DEVELOP\` com \`Refs #$n\`."
      echo "#$n: branch $branch criada."
      criadas=$((criadas + 1))
    fi
    projeto mover "$painel" "$n" "$para" "$de|-"
  done
}

processar "$EXEC" feature "A fazer"   "Feature"
processar "$EXEC" feature "Reprovado" "Code"
processar "$BUGS" bugfix  "Novo"      "Em correção"
processar "$BUGS" bugfix  "Reprovado" "Em correção"
echo "Branches criadas: $criadas."
