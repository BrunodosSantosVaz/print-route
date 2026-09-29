#!/usr/bin/env bash
# "Publicar em producao": o ultimo botao da esteira. Depois de a homologacao (release candidata
# vX.Y.Z-rc.N) ter sido testada e cada cartao marcado "Aprovado", publica a versao e finaliza tudo:
#   1. PORTAO (sempre, inclusive na simulacao) - recusa se:
#        - o milestone nao existe/esta vazio, ou algum cartao (tarefa/bug) nao esta em "Aprovado"
#          (cartao em "Reprovado" e apontado a parte: precisa voltar para "Code", ser corrigido e
#          passar de novo pela esteira, gerando uma nova candidata);
#        - nao ha PR release/x.y.z -> main, ele tem conflito ou checks pendentes/falhando;
#        - conferir-release.sh reprova (sem candidata, ou src/ mudou depois dela, ou sem CHANGELOG);
#   2. mescla o PR na main (commit "chore(release): merge vX.Y.Z");
#   3. promove a MESMA candidata a vX.Y.Z (Latest), sem recompilar (promover-release.sh);
#   4. anuncia no Discussions (anunciar-release.sh); o executavel fica so na Release;
#   5. finaliza: fecha issues, cartoes -> Concluido/Corrigido, epicos -> Concluida, milestone,
#      e apaga as branches das tarefas e a release/x.y.z, que fica so na tag (encerrar-sprint.sh);
#   6. devolve a main para a develop (backmerge.sh).
# Idempotente: se a Release vX.Y.Z ja existe, so refaz os passos 5 e 6 (retomada apos falha).
#
# Variaveis: VERSAO (v0.6.0 ou 0.6.0), SIMULAR=true (so confere o portao e mostra o plano),
# PROJETO_PLANEJAMENTO/EXECUCAO/BUGS, GH_TOKEN, GITHUB_REPOSITORY, BRANCH_MAIN (main),
# BRANCH_DEVELOP (develop). Deve rodar em um clone da main com todas as tags.
set -euo pipefail

AQUI="$(cd "$(dirname "$0")" && pwd)"
EXEC="${PROJETO_EXECUCAO:?}"; BUGS="${PROJETO_BUGS:?}"; : "${PROJETO_PLANEJAMENTO:?}"
R="${GITHUB_REPOSITORY:?}"
MAIN="${BRANCH_MAIN:-main}"
v="${VERSAO:?informe a versao}"; v="${v#v}"; tag="v$v"; branch="release/$v"
SIMULAR="${SIMULAR:-false}"
projeto() { bash "${PROJETO_SH:-$AQUI/projeto.sh}" "$@"; }
falhas=()
falha() { falhas+=("$1"); echo "::error::$1"; }

echo "Publicar $tag em producao${SIMULAR/true/ [SIMULACAO]}"

# ---- ja publicada? (retomada)
if gh release view "$tag" >/dev/null 2>&1; then
  ja_publicada=true
  echo "A Release $tag ja existe: pulo o portao, o merge e a promocao; so finalizo."
else
  ja_publicada=false
fi

if [ "$ja_publicada" = false ]; then
  # ---- portao 1: cartoes do milestone
  m=$(gh api "repos/$R/milestones?state=all&per_page=100" --paginate \
    --jq ".[] | select(.title==\"$tag\") | .number" | head -1)
  if [ -z "$m" ]; then
    falha "Milestone '$tag' nao encontrado. Inicie a sprint dessa versao antes."
  else
    aprovados_exec=" $(projeto cartoes "$EXEC" "Aprovado" | tr '\n' ' ') "
    aprovados_bugs=" $(projeto cartoes "$BUGS" "Aprovado" | tr '\n' ' ') "
    reprovados=" $(projeto cartoes "$EXEC" "Reprovado" | tr '\n' ' ') $(projeto cartoes "$BUGS" "Reprovado" | tr '\n' ' ') "
    total=0; ok=0; pend=(); reprov=()
    while IFS=$'\t' read -r n estado tipo; do
      [ -n "$n" ] || continue
      total=$((total + 1))
      if [ "$estado" = closed ]; then ok=$((ok + 1)); continue; fi
      if [[ "$reprovados" == *" $n "* ]]; then reprov+=("#$n"); continue; fi
      if { [ "$tipo" = bug ] && [[ "$aprovados_bugs" == *" $n "* ]]; } || \
         { [ "$tipo" = task ] && [[ "$aprovados_exec" == *" $n "* ]]; }; then ok=$((ok + 1)); else pend+=("#$n"); fi
    done < <(gh api "repos/$R/issues?milestone=$m&state=all&per_page=100" --paginate \
      --jq '.[] | select(has("pull_request") | not) | select([.labels[].name] | any(. == "task" or . == "bug"))
            | [.number, .state, (if ([.labels[].name] | index("bug")) then "bug" else "task" end)] | @tsv')
    echo "Cartoes do milestone: $total (aprovados/concluidos: $ok)."
    [ "$total" -gt 0 ] || falha "O milestone $tag nao tem tarefas nem bugs."
    [ "${#reprov[@]}" -eq 0 ] || falha "Cartoes REPROVADOS na homologacao: ${reprov[*]}. Devolva-os para 'Code' (a acao 'Criar branches' recria a branch), corrija e passe de novo pela esteira; a nova candidata volta para homologacao."
    [ "${#pend[@]}" -eq 0 ] || falha "Cartoes ainda nao aprovados (devem estar em 'Aprovado'): ${pend[*]}."
  fi

  # ---- portao 2: PR da release e checks
  pr=$(gh pr list --repo "$R" --head "$branch" --base "$MAIN" --state all --json number,state \
    --jq '[.[] | select(.state=="OPEN" or .state=="MERGED")][0] // empty | "\(.number) \(.state)"')
  pr_num="${pr%% *}"; pr_estado="${pr##* }"
  if [ -z "$pr" ]; then
    falha "Nao ha PR $branch -> $MAIN. Ele e aberto pela 'Build release candidata' apos a homologacao."
  elif [ "$pr_estado" = OPEN ]; then
    info=$(gh pr view "$pr_num" --repo "$R" --json mergeable,statusCheckRollup --jq '
      [ .mergeable,
        ([.statusCheckRollup[]
          | select((if (.conclusion // "") != "" then .conclusion else (.state // .status // "") end) as $c
                   | ["SUCCESS","SKIPPED","NEUTRAL"] | index($c) | not)
          | (.name // .context)] | join(", ")) ] | @tsv')
    IFS=$'\t' read -r mergeavel checks_ruins <<<"$info"
    [ "$mergeavel" != CONFLICTING ] || falha "O PR #$pr_num ($branch -> $MAIN) tem conflito."
    [ -z "$checks_ruins" ] || falha "Checks do PR #$pr_num pendentes ou falhando: $checks_ruins."
  fi

  # ---- portao 3: candidata testada e codigo identico (em uma copia da branch da release)
  git fetch --quiet origin "$branch" --tags 2>/dev/null || true
  if git rev-parse --verify --quiet "origin/$branch" >/dev/null; then
    dir_rel=$(mktemp -d); rc_saida=$(mktemp)
    git worktree add --quiet --detach "$dir_rel" "origin/$branch"
    if (cd "$dir_rel" && GITHUB_OUTPUT="$rc_saida" bash "$AQUI/conferir-release.sh"); then
      rc_tag=$(sed -n 's/^rc_tag=//p' "$rc_saida" | tail -1)
    else
      falha "conferir-release reprovou $branch (veja acima)."
    fi
    git worktree remove --force "$dir_rel" || true
  else
    falha "Branch $branch nao encontrada. Ela e criada por 'Integrar release'."
  fi

  if [ "${#falhas[@]}" -gt 0 ]; then
    echo; echo "Publicacao RECUSADA (${#falhas[@]} problema(s)). Nada foi alterado."
    exit 1
  fi
  echo "Portao aprovado: candidata $rc_tag, $ok cartao(oes) aprovado(s), PR ${pr_num:-?} (${pr_estado:-?})."
fi

# ---- simulacao: so mostra o plano
if [ "$SIMULAR" = true ]; then
  if [ "$ja_publicada" = false ]; then
    [ "$pr_estado" != OPEN ] || echo "[simulado] mesclar PR #$pr_num ($branch -> $MAIN) como 'chore(release): merge $tag'"
    echo "[simulado] promover $rc_tag a $tag (Latest, sem recompilar)"
    echo "[simulado] anunciar $tag no Discussions"
  fi
  VERSAO="$v" SIMULAR=true bash "$AQUI/encerrar-sprint.sh"
  DRY_RUN=1 TAG="$tag" bash "$AQUI/backmerge.sh"
  echo "Simulacao concluida: nada foi alterado."
  exit 0
fi

# ---- publicacao de verdade
if [ "$ja_publicada" = false ]; then
  if [ "$pr_estado" = OPEN ]; then
    # --admin: o dono contorna o ruleset (o "ok" humano e o botao + a aprovacao do ambiente producao)
    gh pr merge "$pr_num" --repo "$R" --merge --admin \
      --subject "chore(release): merge $tag" --body "Publicação de $tag (promove a candidata $rc_tag). PR #$pr_num."
  else
    echo "PR #$pr_num ja estava mesclado."
  fi
  git fetch --quiet origin "$MAIN" --tags
  git checkout --quiet --detach "origin/$MAIN"
  sha=$(git rev-parse HEAD)
  versao_main=$(bash "$AQUI/versao.sh")
  [ "$versao_main" = "$v" ] || { echo "::error::A $MAIN esta na versao '$versao_main', esperado '$v'. Nada publicado."; exit 1; }
  # o merge nao deve ter alterado o binario testado
  GITHUB_OUTPUT=/dev/null bash "$AQUI/conferir-release.sh"

  RC_TAG="$rc_tag" TARGET_SHA="$sha" bash "$AQUI/promover-release.sh"
  TAG="$tag" bash "$AQUI/anunciar-release.sh" || true
fi

# ---- finalizar e devolver a main
VERSAO="$v" SIMULAR=false bash "$AQUI/encerrar-sprint.sh"
git fetch --quiet origin "$MAIN" --tags
TAG="$tag" bash "$AQUI/backmerge.sh"
echo "Producao: $tag publicada e sprint encerrada."
