#!/usr/bin/env bash
# Depois que a release candidata (vX.Y.Z-rc.N) foi criada: leva release/x.y.z para a develop,
# move os cartoes do milestone para "Homologacao" e abre o PR da release para a main (se ainda
# nao existe). Chamado pelo workflow "Build release candidata".
#
# Variaveis: BRANCH (release/x.y.z), RC_TAG, PROJETO_EXECUCAO, PROJETO_BUGS, BRANCH_DEVELOP.
set -euo pipefail

AQUI="$(cd "$(dirname "$0")" && pwd)"
EXEC="${PROJETO_EXECUCAO:?}"; BUGS="${PROJETO_BUGS:?}"
R="$GITHUB_REPOSITORY"
DEVELOP="${BRANCH_DEVELOP:-develop}"; MAIN="${BRANCH_MAIN:-main}"
branch="${BRANCH:?}"; rc_tag="${RC_TAG:?}"; v="${branch#release/}"; tag="v$v"
projeto() { bash "$AQUI/projeto.sh" "$@"; }

# ---- release -> develop
rc=0
saida=$(bash "$AQUI/mesclar.sh" "$DEVELOP" "$DEVELOP" "$branch=refs/heads/$branch") || rc=$?
echo "$saida"
if [ "$rc" -eq 3 ]; then
  echo "::error::Conflito ao levar $branch para a $DEVELOP. Resolva manualmente (merge da $DEVELOP na $branch) e envie a branch."; exit 1
elif [ "$rc" -ne 0 ]; then exit "$rc"; fi
if grep -q '^MESCLADO' <<<"$saida"; then git push origin "$DEVELOP"; fi

# ---- cartoes do milestone -> Homologacao
m=$(gh api "repos/$R/milestones?state=all&per_page=100" --paginate --jq ".[] | select(.title==\"$tag\") | .number" | head -1)
if [ -n "$m" ]; then
  while IFS=$'\t' read -r n tipo semexe; do
    [ -n "$n" ] || continue
    painel="$EXEC"; [ "$tipo" = bug ] && painel="$BUGS"
    # sem-executavel: nao ha o que testar no .exe, entao vai direto para Aprovado
    destino="Homologação"; [ "$semexe" = true ] && destino="Aprovado"
    projeto mover "$painel" "$n" "$destino" "CI/PR|Code|Feature|Homologação" || true
  done < <(gh api "repos/$R/issues?milestone=$m&state=open&per_page=100" --paginate \
    --jq '.[] | select(has("pull_request") | not) | select([.labels[].name] | any(. == "task" or . == "bug"))
          | [.number, (if ([.labels[].name] | index("bug")) then "bug" else "task" end),
             (if ([.labels[].name] | index("sem-executavel")) then "true" else "false" end)] | @tsv')
fi

# ---- PR da release para a main
existente=$(gh pr list --repo "$R" --head "$branch" --base "$MAIN" --state open --json number --jq '.[0].number // empty')
if [ -z "$existente" ]; then
  gh pr create --repo "$R" --base "$MAIN" --head "$branch" --title "release: $v" --body "## Release $tag

Homologação: release candidata \`$rc_tag\` (pre-release nas Releases), já integrada na \`$DEVELOP\`.

Depois de aprovar todas as tarefas em **Homologação** (mova para *Aprovado*; *Reprovado* volta para *Code*), rode a ação **Publicar em produção**: ela mescla este PR, promove a candidata a \`$tag\`, encerra as issues e apaga as branches das tarefas."
else
  echo "PR #$existente da release para a $MAIN ja existe."
fi
echo "Homologacao de $tag pronta ($rc_tag)."
