#!/usr/bin/env bash
# Finaliza a sprint/release DEPOIS de publicada em producao. Chamado pela acao "Publicar em
# producao" (publicar-producao.sh), pelo pos-deploy.sh (hotfix/release mesclada na mao) e pelo
# botao "Encerrar sprint" (refazer/completar a limpeza, idempotente).
#   - fecha as issues do milestone e move os cartoes (tarefas -> Concluido,
#     bugs -> Corrigido);
#   - fecha os epicos cujas sub-issues estao todas concluidas (-> Concluida);
#   - fecha o milestone;
#   - apaga as branches feature/bugfix/hotfix ja mescladas;
#   - apaga a release/x.y.z da versao (apagar-release.sh), so se a tag vX.Y.Z e a Release existem e a
#     branch esta contida na tag e na main. O historico da versao fica na TAG (padrao GitFlow); no
#     repositorio sobram main e develop.
#
# Variaveis: VERSAO (ex.: v0.6.0 ou 0.6.0), SIMULAR=true (so mostra), PROJETO_*.
set -euo pipefail

AQUI="$(cd "$(dirname "$0")" && pwd)"
PLAN="${PROJETO_PLANEJAMENTO:?}"; EXEC="${PROJETO_EXECUCAO:?}"; BUGS="${PROJETO_BUGS:?}"
R="$GITHUB_REPOSITORY"; OWNER="${R%%/*}"; REPO="${R##*/}"
v="${VERSAO:?informe a versao}"; v="${v#v}"; tag="v$v"

SIMULAR="${SIMULAR:-false}"
[ "$SIMULAR" = true ] && export DRY_RUN=1
run() { if [ "$SIMULAR" = true ]; then echo "[simulado] $*"; else "$@"; fi; }
projeto() { bash "$AQUI/projeto.sh" "$@"; }

m=$(gh api "repos/$R/milestones?state=all&per_page=100" --paginate \
  --jq ".[] | select(.title==\"$tag\" or .title==\"$v\") | .number" | head -1)
if [ -z "$m" ]; then echo "::error::Milestone '$tag' nao encontrado."; exit 1; fi
echo "Encerrando $tag (milestone #$m)${SIMULAR/true/ [SIMULACAO]}"

linhas=$(gh api "repos/$R/issues?milestone=$m&state=all&per_page=100" --paginate \
  --jq '.[] | select(has("pull_request") | not)
        | [.number, .state, ([.labels[].name] | join(","))] | @tsv')
[ -n "$linhas" ] || echo "Milestone sem issues."

numeros=(); pais=()
while IFS=$'\t' read -r n estado labels; do
  [ -n "$n" ] || continue
  numeros+=("$n")
  if [ "$estado" = open ]; then
    run gh issue close "$n" --reason completed --comment "Publicado em produção na versão $tag."
  fi
  if   [[ ",$labels," == *",bug,"*  ]]; then projeto mover "$BUGS" "$n" "Corrigido"
  elif [[ ",$labels," == *",task,"* ]]; then projeto mover "$EXEC" "$n" "Concluído"
  fi
  pai=$(gh api graphql -f o="$OWNER" -f r="$REPO" -F n="$n" -f query='
    query($o:String!,$r:String!,$n:Int!){ repository(owner:$o,name:$r){
      issue(number:$n){ parent{ number } } } }' --jq '.data.repository.issue.parent.number // empty')
  [ -z "$pai" ] || pais+=("$pai")
done <<<"$linhas"

# ---- epicos: fecha os que ficaram com todas as sub-issues concluidas
for p in $(printf '%s\n' "${pais[@]:-}" | sort -un); do
  [ -n "$p" ] || continue
  if [ "$SIMULAR" = true ]; then echo "[simulado] verificar epico #$p (fecha se todas as sub-issues concluidas)"; continue; fi
  sleep 2
  resumo=$(gh api graphql -f o="$OWNER" -f r="$REPO" -F n="$p" -f query='
    query($o:String!,$r:String!,$n:Int!){ repository(owner:$o,name:$r){
      issue(number:$n){ state subIssuesSummary{ total completed } } } }' \
    --jq '.data.repository.issue | "\(.state) \(.subIssuesSummary.total) \(.subIssuesSummary.completed)"')
  read -r estado total feitas <<<"$resumo"
  if [ "$total" -gt 0 ] && [ "$total" = "$feitas" ]; then
    [ "$estado" = OPEN ] && gh issue close "$p" --reason completed --comment "Todas as tarefas em produção ($tag)."
    projeto mover "$PLAN" "$p" "Concluída"
  else
    echo "Epico #$p segue aberto ($feitas/$total tarefas concluidas)."
  fi
done

# ---- milestone
run gh api -X PATCH "repos/$R/milestones/$m" -f state=closed >/dev/null

# ---- branches ja mescladas das tarefas da sprint
if [ "${#numeros[@]}" -gt 0 ]; then
  alt=$(IFS='|'; echo "${numeros[*]}")
else
  alt="-"
fi
refs=$(gh api "repos/$R/pulls?state=closed&per_page=100" --paginate \
  --jq '.[] | select(.merged_at != null) | .head.ref' \
  | grep -E "^(feature|bugfix|hotfix)/($alt)-" | sort -u || true)
for ref in $refs; do
  if [ "$SIMULAR" = true ]; then echo "[simulado] apagar branch $ref"
  elif gh api -X DELETE "repos/$R/git/refs/heads/$ref" >/dev/null 2>&1; then echo "Branch apagada: $ref"
  else echo "Branch ja nao existe: $ref"; fi
done
# ---- branch da release: temporaria (GitFlow); a versao fica na tag. Travas em apagar-release.sh.
VERSAO="$v" SIMULAR="$SIMULAR" bash "$AQUI/apagar-release.sh" \
  || echo "::warning::Nao consegui conferir/apagar release/$v (a sprint foi encerrada mesmo assim)."
echo "Sprint $tag encerrada."
