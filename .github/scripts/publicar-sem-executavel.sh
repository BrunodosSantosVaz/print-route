#!/usr/bin/env bash
# "Publicar sem executavel": leva para a main as mudancas que NAO alteram o programa (docs, testes,
# workflows, scripts) e finaliza as issues marcadas `sem-executavel`, sem versao, sem candidata e sem
# Release nova. Roda quando voce quer que a main receba o que ja esta na develop e concluir essas issues.
#
# PORTAO (recusa, sem alterar nada, se):
#   - src/ ou requirements-build.txt diferem entre a main e a develop (ha mudanca de programa nao
#     publicada: faca uma release normal, com homologacao);
#   - a main nao e ancestral da develop (divergiram, ex.: hotfix ainda nao devolvido: rode o back-merge);
#   - o check `check` da ponta da develop nao esta concluido com sucesso.
# DEPOIS DO PORTAO:
#   1. avanca a main ate a develop (fast-forward: sem commit de merge e sem back-merge);
#   2. para cada issue ABERTA com a label `sem-executavel` cujo cartao esta em "Aprovado": fecha,
#      cartao -> Concluido (tarefa) / Corrigido (bug), conclui o epico se era a ultima tarefa e apaga
#      a branch feature/bugfix ja mesclada. Issues com a label que ainda nao estao em Aprovado seguem abertas.
# Idempotente. Variaveis: SIMULAR=true (so mostra o plano), PROJETO_EXECUCAO/BUGS, GH_TOKEN,
# GITHUB_REPOSITORY, BRANCH_MAIN (main), BRANCH_DEVELOP (develop), PROJETO_SH (testes).
set -euo pipefail

AQUI="$(cd "$(dirname "$0")" && pwd)"
EXEC="${PROJETO_EXECUCAO:?}"; BUGS="${PROJETO_BUGS:?}"; : "${PROJETO_PLANEJAMENTO:?}"
R="${GITHUB_REPOSITORY:?}"; OWNER="${R%%/*}"; REPO="${R##*/}"
MAIN="${BRANCH_MAIN:-main}"; DEVELOP="${BRANCH_DEVELOP:-develop}"
SIMULAR="${SIMULAR:-false}"
projeto() { bash "${PROJETO_SH:-$AQUI/projeto.sh}" "$@"; }
gql() { gh api graphql -H "GraphQL-Features: sub_issues" "$@"; }
falhas=()
falha() { falhas+=("$1"); echo "::error::$1"; }

echo "Publicar sem executavel${SIMULAR/true/ [SIMULACAO]}"
git fetch --quiet origin "$MAIN" "$DEVELOP"

# ---- portao 1: nada do programa mudou
mudou=$(git diff --name-only "origin/$MAIN" "origin/$DEVELOP" -- src requirements-build.txt)
if [ -n "$mudou" ]; then
  falha "Ha mudanca no programa ainda nao publicada ($(echo "$mudou" | tr '\n' ' ')). Isto exige release com homologacao (Integrar release e Publicar em producao)."
fi
# ---- portao 2: avanco simples
if ! git merge-base --is-ancestor "origin/$MAIN" "origin/$DEVELOP"; then
  falha "A $MAIN tem commits que a $DEVELOP nao tem (divergiram). Devolva a $MAIN para a $DEVELOP (back-merge) antes."
fi
# ---- portao 3: CI da develop
sha=$(git rev-parse "origin/$DEVELOP")
ci=$(gh api "repos/$R/commits/$sha/check-runs?per_page=100" --jq '[.check_runs[] | select(.name=="check")]
  | if length > 0 and (map(.status) | all(. == "completed")) and (map(.conclusion) | all(. == "success")) then "ok" else "pendente" end')
[ "$ci" = ok ] || falha "O check 'check' da ponta da $DEVELOP (${sha:0:7}) esta pendente ou falhando."

# ---- issues sem-executavel abertas
aprov=" $(projeto cartoes "$EXEC" Aprovado | tr '\n' ' ') $(projeto cartoes "$BUGS" Aprovado | tr '\n' ' ') "
reprov=" $(projeto cartoes "$EXEC" Reprovado | tr '\n' ' ') $(projeto cartoes "$BUGS" Reprovado | tr '\n' ' ') "
finalizar=(); seguem=(); reprovadas=()
while IFS=$'\t' read -r n tipo; do
  [ -n "$n" ] || continue
  if   [[ "$aprov"   == *" $n "* ]]; then finalizar+=("$n:$tipo")
  elif [[ "$reprov"  == *" $n "* ]]; then reprovadas+=("#$n")
  else seguem+=("#$n"); fi
done < <(gh api "repos/$R/issues?labels=sem-executavel&state=open&per_page=100" --paginate \
  --jq '.[] | select(has("pull_request") | not) | [.number, (if ([.labels[].name] | index("bug")) then "bug" else "task" end)] | @tsv')

if [ "${#falhas[@]}" -gt 0 ]; then
  echo; echo "Publicacao RECUSADA (${#falhas[@]} problema(s)). Nada foi alterado."; exit 1
fi
[ "${#reprovadas[@]}" -eq 0 ] || echo "::warning::Issues sem-executavel REPROVADAS (nao finalizadas): ${reprovadas[*]}."
[ "${#seguem[@]}" -eq 0 ] || echo "Seguem abertas (ainda nao estao em Aprovado): ${seguem[*]}."

atrasada=false; git merge-base --is-ancestor "origin/$DEVELOP" "origin/$MAIN" || atrasada=true
echo "Portao aprovado. Main $([ "$atrasada" = true ] && echo "esta atras da $DEVELOP e sera avancada" || echo "ja esta na $DEVELOP"); issues a finalizar: ${#finalizar[@]}."

if [ "$SIMULAR" = true ]; then
  [ "$atrasada" = false ] || echo "[simulado] avancar $MAIN ate ${sha:0:7} (fast-forward de origin/$DEVELOP)"
  for item in "${finalizar[@]:-}"; do [ -n "$item" ] && echo "[simulado] fechar #${item%%:*} e mover o cartao para Concluido/Corrigido"; done
  echo "Simulacao concluida: nada foi alterado."; exit 0
fi

# ---- 1. avancar a main
if [ "$atrasada" = true ]; then
  git push origin "origin/$DEVELOP:refs/heads/$MAIN"
  echo "$MAIN avancada ate ${sha:0:7}."
fi

# ---- 2. finalizar as issues
pais=(); numeros=()
for item in "${finalizar[@]:-}"; do
  [ -n "$item" ] || continue
  n="${item%%:*}"; tipo="${item##*:}"; numeros+=("$n")
  gh issue close "$n" --repo "$R" --reason completed \
    --comment "Concluída sem executável: a mudança não altera o programa (documentação, testes ou automação) e já está na \`$MAIN\`."
  if [ "$tipo" = bug ]; then projeto mover "$BUGS" "$n" "Corrigido"; else projeto mover "$EXEC" "$n" "Concluído"; fi
  pai=$(gql -f o="$OWNER" -f r="$REPO" -F n="$n" -f query='
    query($o:String!,$r:String!,$n:Int!){ repository(owner:$o,name:$r){ issue(number:$n){ parent{ number } } } }' \
    --jq '.data.repository.issue.parent.number // empty')
  [ -z "$pai" ] || pais+=("$pai")
done

# epicos que ficaram com todas as tarefas concluidas
for p in $(printf '%s\n' "${pais[@]:-}" | sort -un); do
  [ -n "$p" ] || continue
  sleep 2
  resumo=$(gql -f o="$OWNER" -f r="$REPO" -F n="$p" -f query='
    query($o:String!,$r:String!,$n:Int!){ repository(owner:$o,name:$r){
      issue(number:$n){ state subIssuesSummary{ total completed } } } }' \
    --jq '.data.repository.issue | "\(.state) \(.subIssuesSummary.total) \(.subIssuesSummary.completed)"')
  read -r estado total feitas <<<"$resumo"
  if [ "$total" -gt 0 ] && [ "$total" = "$feitas" ]; then
    [ "$estado" != OPEN ] || gh issue close "$p" --repo "$R" --reason completed --comment "Todas as tarefas concluídas."
    projeto mover "$PROJETO_PLANEJAMENTO" "$p" "Concluída"
  else
    echo "Epico #$p segue aberto ($feitas/$total tarefas concluidas)."
  fi
done

# branches feature/bugfix ja mescladas das issues finalizadas
if [ "${#numeros[@]}" -gt 0 ]; then
  alt=$(IFS='|'; echo "${numeros[*]}")
  refs=$(gh api "repos/$R/pulls?state=closed&per_page=100" --paginate \
    --jq '.[] | select(.merged_at != null) | .head.ref' | grep -E "^(feature|bugfix)/($alt)-" | sort -u || true)
  for ref in $refs; do
    if gh api -X DELETE "repos/$R/git/refs/heads/$ref" >/dev/null 2>&1; then echo "Branch apagada: $ref"; fi
  done
fi
echo "Publicacao sem executavel concluida."
