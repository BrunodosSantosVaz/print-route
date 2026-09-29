#!/usr/bin/env bash
# Devolve a main para a develop (back-merge) depois de uma publicacao, para que a develop conheca o
# commit de merge da release e qualquer hotfix. Idempotente: se a develop ja contem a main, nao faz nada.
# Conflito => erro (resolver manualmente com uma branch chore/back-merge-<tag> + PR).
# Variaveis: TAG, BRANCH_DEVELOP (develop), BRANCH_MAIN (main), DRY_RUN=1 para simular.
set -euo pipefail
tag="${TAG:-}"; DEVELOP="${BRANCH_DEVELOP:-develop}"; MAIN="${BRANCH_MAIN:-main}"

if [ "${DRY_RUN:-}" = 1 ]; then echo "[simulado] back-merge origin/$MAIN -> $DEVELOP"; exit 0; fi
git config user.name  >/dev/null 2>&1 || git config user.name  "github-actions[bot]"
git config user.email >/dev/null 2>&1 || git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
git fetch origin "$DEVELOP" "$MAIN"
if git merge-base --is-ancestor "origin/$MAIN" "origin/$DEVELOP"; then
  echo "'$DEVELOP' ja contem '$MAIN'; nada a devolver."; exit 0
fi
git checkout -B "$DEVELOP" "origin/$DEVELOP"
if ! git merge --no-ff "origin/$MAIN" -m "chore: back-merge $MAIN into $DEVELOP${tag:+ ($tag)}"; then
  git merge --abort || true
  echo "::error::Conflito no back-merge $MAIN -> $DEVELOP. Resolva manualmente (branch chore/back-merge${tag:+-$tag} + PR)."
  exit 1
fi
git push origin "$DEVELOP"
echo "Back-merge concluido."
