#!/usr/bin/env bash
# "Integrar release": com TODOS os PRs de um milestone aprovados (label "aprovado") e com a CI verde,
# cria (ou reaproveita) release/x.y.z a partir da develop, mescla as features UMA POR UMA, atualiza a
# versao (arquivo de versao, via versao.sh) e o CHANGELOG e envia a branch. O push dispara o workflow "Build release
# candidata" (testes, build, pre-release vX.Y.Z-rc.N) e, depois dele, a homologacao (ver
# homologar-release.sh).
#
# Tudo ou nada: se falta aprovar/esperar CI de algum PR, nada e feito; se um merge da conflito, nada
# e enviado (o PR volta para "Code", sem a label, com um comentario). Modo automatico (AUTO=true,
# disparado quando um PR recebe a label "aprovado"): se ainda faltam PRs, sai sem erro.
#
# PR `sem-executavel` (o PR ou a issue dele tem a label) NUNCA e integrado: nao muda o programa, entao
# nao gera versao, branch de release nem candidata. Ele e mesclado direto na develop e finalizado por
# "Publicar sem executavel". Esta trava vale mesmo com a label "aprovado" no PR.
#
# Variaveis: VERSAO (v0.6.0; no modo automatico sai do milestone do PR), PR_NUMBER, AUTO, SIMULAR=true,
# PROJETO_EXECUCAO, PROJETO_BUGS, BRANCH_DEVELOP (develop).
set -euo pipefail

AQUI="$(cd "$(dirname "$0")" && pwd)"
EXEC="${PROJETO_EXECUCAO:?}"; BUGS="${PROJETO_BUGS:?}"
R="$GITHUB_REPOSITORY"
DEVELOP="${BRANCH_DEVELOP:-develop}"
SIMULAR="${SIMULAR:-false}"; AUTO="${AUTO:-false}"
[ "$SIMULAR" = true ] && export DRY_RUN=1
projeto() { bash "$AQUI/projeto.sh" "$@"; }
falta() { # mensagem: no modo automatico e so um aviso
  if [ "$AUTO" = true ]; then echo "::notice::$1"; exit 0; else echo "::error::$1"; exit 1; fi
}

# ---- trava: PR sem-executavel nao vira versao
if [ -n "${PR_NUMBER:-}" ]; then
  rotulos=$(gh api "repos/$R/issues/$PR_NUMBER" --jq '[.labels[].name] | join(",")')
  head=$(gh api "repos/$R/pulls/$PR_NUMBER" --jq .head.ref)
  if [[ "$head" =~ ^(feature|bugfix)/([0-9]+)- ]]; then
    rotulos+=",$(gh api "repos/$R/issues/${BASH_REMATCH[2]}" --jq '[.labels[].name] | join(",")')"
  fi
  if [[ ",$rotulos," == *",sem-executavel,"* ]]; then
    echo "::notice::PR #$PR_NUMBER e sem-executavel (nao muda o programa): nao entra em versao nem em release. Mescle direto na $DEVELOP e finalize com 'Publicar sem executavel'."
    exit 0
  fi
fi

v="${VERSAO:-}"
if [ -z "$v" ] && [ -n "${PR_NUMBER:-}" ]; then
  head=$(gh api "repos/$R/pulls/$PR_NUMBER" --jq .head.ref)
  if [[ "$head" =~ ^(feature|bugfix)/([0-9]+)- ]]; then
    v=$(gh api "repos/$R/issues/${BASH_REMATCH[2]}" --jq '.milestone.title // ""')
  fi
  [ -n "$v" ] || { echo "PR #$PR_NUMBER nao esta ligado a um milestone; nada a integrar."; exit 0; }
fi
v="${v#v}"; tag="v$v"; branch="release/$v"
[[ "$v" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "::error::Versao '$v' invalida (use x.y.z)."; exit 1; }

m=$(gh api "repos/$R/milestones?state=all&per_page=100" --paginate --jq ".[] | select(.title==\"$tag\") | .number" | head -1)
[ -n "$m" ] || falta "Milestone $tag nao encontrado."

# ---- itens do milestone (tarefas e bugs): numero, estado, tipo, titulo
itens_tsv=$(gh api "repos/$R/issues?milestone=$m&state=all&per_page=100" --paginate \
  --jq '.[] | select(has("pull_request") | not) | select([.labels[].name] | any(. == "task" or . == "bug"))
        | [.number, .state, (if ([.labels[].name] | index("bug")) then "bug" else "task" end),
           (if ([.labels[].name] | index("sem-executavel")) then "true" else "false" end), .title] | @tsv')
[ -n "$itens_tsv" ] || falta "Milestone $tag sem tarefas ou bugs."

refs=(); pendentes=(); declare -A pr_do_item tipo_do_item
while IFS=$'\t' read -r n estado tipo semexe titulo; do
  [ -n "$n" ] || continue
  [ "$estado" = open ] || continue                       # ja concluida: nao precisa de PR
  tipo_do_item[$n]=$tipo
  pr=$(gh api "repos/$R/pulls?state=open&base=$DEVELOP&per_page=100" --paginate \
    --jq ".[] | select(.head.ref | test(\"^(feature|bugfix)/$n-\")) | [.number, ([.labels[].name] | join(\",\")), .head.sha] | @tsv" | head -1)
  if [ -z "$pr" ]; then
    # sem PR aberto: tudo bem se o PR ja foi mesclado (integrado em uma candidata anterior e agora em
    # homologacao); senao falta o PR
    mesclado=$(gh api "repos/$R/pulls?state=closed&base=$DEVELOP&per_page=100" --paginate \
      --jq ".[] | select(.merged_at != null) | select(.head.ref | test(\"^(feature|bugfix)/$n-\")) | .number" | wc -l)
    if [ "${mesclado:-0}" -gt 0 ]; then echo "#$n ja integrada em uma candidata anterior."; else pendentes+=("#$n sem PR aberto para a $DEVELOP"); fi
    continue
  fi
  IFS=$'\t' read -r prn labels sha <<<"$pr"
  if [[ ",$labels," != *",aprovado,"* ]]; then pendentes+=("#$n (PR #$prn) sem a label 'aprovado'"); continue; fi
  ci=$(gh api "repos/$R/commits/$sha/check-runs?per_page=100" --jq '[.check_runs[] | select(.name=="check" or .name=="regras")]
    | if (map(.status) | all(. == "completed")) and ((map(select(.conclusion == "success") | .name) | unique) == ["check","regras"]) then "ok" else "pendente" end')
  if [ "$ci" != ok ]; then pendentes+=("#$n (PR #$prn) com a CI pendente ou falhando"); continue; fi
  refs+=("PR#$prn=refs/pull/$prn/head"); pr_do_item[$n]=$prn
done <<<"$itens_tsv"

if [ "${#pendentes[@]}" -gt 0 ]; then
  printf '%s\n' "${pendentes[@]}" | sed 's/^/  - /'
  falta "Ainda nao da para integrar $tag: ${#pendentes[@]} item(ns) pendente(s) (lista acima)."
fi
echo "Integrando $tag: ${#refs[@]} PR(s) aprovado(s) em $branch."
if [ "$SIMULAR" = true ]; then
  for r in "${refs[@]}"; do echo "[simulado] mesclar $r em $branch (--no-ff)"; done
  echo "[simulado] atualizar $(bash "$AQUI/versao.sh" --arquivo) e CHANGELOG.md para $v; enviar $branch (dispara a release candidata)"
  exit 0
fi

# ---- merges, um por um (tudo ou nada)
rc=0
saida=$(bash "$AQUI/mesclar.sh" "$branch" "$DEVELOP" "${refs[@]}") || rc=$?
echo "$saida"
if [ "$rc" -eq 3 ]; then
  rotulo=$(awk '/^CONFLITO/{print $2}' <<<"$saida"); prn="${rotulo#PR#}"
  for n in "${!pr_do_item[@]}"; do
    [ "${pr_do_item[$n]}" = "$prn" ] || continue
    painel="$EXEC"; [ "${tipo_do_item[$n]}" = bug ] && painel="$BUGS"
    projeto mover "$painel" "$n" "Code" "CI/PR|Homologação|Aprovado" || true
  done
  gh pr comment "$prn" --repo "$R" --body "Conflito ao integrar este PR em \`$branch\`. Atualize a branch com a \`$DEVELOP\` (merge ou rebase), resolva o conflito e aplique a label \`aprovado\` de novo. Nada foi enviado para a release."
  gh pr edit "$prn" --repo "$R" --remove-label aprovado >/dev/null || true
  echo "::error::Conflito no PR #$prn: ele voltou para 'Code'. Nada foi enviado."; exit 1
elif [ "$rc" -ne 0 ]; then
  exit "$rc"
fi

# ---- versao e CHANGELOG
# itens `sem-executavel` (docs, CI) nao entram nas notas: nao mudam o programa
jq -R -s 'split("\n") | map(select(length > 0) | split("\t") | select(.[3] != "true") | {numero: (.[0] | tonumber), tipo: .[2], titulo: .[4]})' \
  <<<"$itens_tsv" > "${RUNNER_TEMP:-/tmp}/itens.json"
python3 "$AQUI/atualizar_release.py" --versao "$v" --data "$(date -u +%F)" --itens "${RUNNER_TEMP:-/tmp}/itens.json"
git add "$(bash "$AQUI/versao.sh" --arquivo)" CHANGELOG.md
if ! git diff --cached --quiet; then git commit -q -m "chore(release): v$v"; fi

if git diff --quiet "origin/$branch" HEAD 2>/dev/null && git rev-parse -q --verify "origin/$branch" >/dev/null; then
  echo "A $branch ja esta atualizada; nada novo para enviar (nenhuma nova candidata)."
else
  git push origin "$branch"
  echo "Enviada: $branch. O workflow 'Build release candidata' gera a pre-release ${tag}-rc.N e depois leva para a homologacao."
fi
