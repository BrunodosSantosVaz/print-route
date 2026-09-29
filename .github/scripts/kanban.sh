#!/usr/bin/env bash
# Move os cartoes dos paineis conforme eventos do GitHub (chamado por
# .github/workflows/kanban.yml). Le tudo de variaveis de ambiente.
#
# Variaveis: EVENT (issues|push|pull_request), ACTION, ISSUE, REF_NAME, CREATED,
# DELETED, HEAD_REF, BASE_REF, MERGED, DRAFT; PROJETO_PLANEJAMENTO/EXECUCAO/BUGS
# (numeros dos paineis); BRANCH_DEVELOP (padrao develop).
set -euo pipefail

AQUI="$(cd "$(dirname "$0")" && pwd)"
PLAN="${PROJETO_PLANEJAMENTO:?}"; EXEC="${PROJETO_EXECUCAO:?}"; BUGS="${PROJETO_BUGS:?}"
DEVELOP="${BRANCH_DEVELOP:-develop}"

mover() { bash "$AQUI/projeto.sh" mover "$@"; }
gql() { gh api graphql -H "GraphQL-Features: sub_issues" "$@"; }

# Fechou uma tarefa/bug: cartao para Concluido/Corrigido e, se era a ultima tarefa do epico,
# o epico tambem e concluido (fechado e movido para "Concluida").
concluir() {
  local labels pai resumo estado total feitas
  labels=$(gh api "repos/$GITHUB_REPOSITORY/issues/$ISSUE" --jq '[.labels[].name] | join(",")')
  [[ ",$labels," == *",task,"* ]] && mover "$EXEC" "$ISSUE" "Concluído"
  [[ ",$labels," == *",bug,"*  ]] && mover "$BUGS" "$ISSUE" "Corrigido"
  pai=$(gql -f o="${GITHUB_REPOSITORY%%/*}" -f r="${GITHUB_REPOSITORY##*/}" -F n="$ISSUE" -f query='
    query($o:String!,$r:String!,$n:Int!){ repository(owner:$o,name:$r){
      issue(number:$n){ parent{ number } } } }' --jq '.data.repository.issue.parent.number // empty')
  [ -n "$pai" ] || return 0
  sleep 3
  resumo=$(gql -f o="${GITHUB_REPOSITORY%%/*}" -f r="${GITHUB_REPOSITORY##*/}" -F n="$pai" -f query='
    query($o:String!,$r:String!,$n:Int!){ repository(owner:$o,name:$r){
      issue(number:$n){ state subIssuesSummary{ total completed } } } }' \
    --jq '.data.repository.issue | "\(.state) \(.subIssuesSummary.total) \(.subIssuesSummary.completed)"')
  read -r estado total feitas <<<"$resumo"
  if [ "$total" -gt 0 ] && [ "$total" = "$feitas" ]; then
    [ "$estado" = OPEN ] && gh issue close "$pai" --repo "$GITHUB_REPOSITORY" --reason completed \
      --comment "Todas as tarefas deste épico foram concluídas."
    mover "$PLAN" "$pai" "Concluída" "Em desenvolvimento"
  else
    echo "Epico #$pai segue aberto ($feitas/$total tarefas concluidas)."
  fi
}

# "feature/12-nome" -> "feature 12"; vazio se nao segue o padrao.
parse_branch() {
  if [[ "$1" =~ ^(feature|bugfix|hotfix)/([0-9]+)- ]]; then
    echo "${BASH_REMATCH[1]} ${BASH_REMATCH[2]}"
  fi
}

# Epico novo que declarou no formulario que NAO muda o programa: label sem-executavel (sprint sem
# versao). So na abertura: depois disso a label e do dono (pode por ou tirar a mao).
marcar_sem_executavel() {
  [ "${ACTION:-}" = opened ] || return 0
  local resposta
  resposta=$(gh api "repos/$GITHUB_REPOSITORY/issues/$ISSUE" --jq '.body // ""' | bash "$AQUI/muda-programa.sh")
  if [ "$resposta" = nao ]; then
    gh issue edit "$ISSUE" --repo "$GITHUB_REPOSITORY" --add-label sem-executavel >/dev/null
    echo "Epico #$ISSUE nao muda o programa: label sem-executavel (sprint sem versao)."
  fi
}

case "${EVENT:?}" in
  issues)
    if [ "${ACTION:-}" = closed ]; then concluir; exit 0; fi
    for label in $(gh api "repos/$GITHUB_REPOSITORY/issues/$ISSUE" --jq '.labels[].name'); do
      case "$label" in
        epic) mover "$PLAN" "$ISSUE" "Brainstorm" "-"; marcar_sem_executavel ;;
        task) mover "$EXEC" "$ISSUE" "A fazer" "-" ;;
        bug)  mover "$BUGS" "$ISSUE" "Novo" "-" ;;
      esac
    done
    if [ "${ACTION:-}" = reopened ]; then
      for label in $(gh api "repos/$GITHUB_REPOSITORY/issues/$ISSUE" --jq '.labels[].name'); do
        case "$label" in
          task) mover "$EXEC" "$ISSUE" "A fazer" ;;
          bug)  mover "$BUGS" "$ISSUE" "Novo" ;;
        esac
      done
    fi
    ;;

  push)
    [ "${DELETED:-false}" = true ] && exit 0
    read -r tipo n <<<"$(parse_branch "${REF_NAME:?}")"
    [ -n "${n:-}" ] || exit 0
    if [ "$tipo" = feature ]; then
      if [ "${CREATED:-false}" = true ]; then
        mover "$EXEC" "$n" "Feature" "A fazer|-|Reprovado"
      else
        mover "$EXEC" "$n" "Code" "A fazer|Feature|Reprovado"
      fi
    else
      mover "$BUGS" "$n" "Em correção" "Novo|-|Reprovado"
    fi
    ;;

  pull_request)
    read -r tipo n <<<"$(parse_branch "${HEAD_REF:?}")"
    [ -n "${n:-}" ] || exit 0
    case "${ACTION:?}" in
      opened|reopened|ready_for_review)
        if [ "${DRAFT:-false}" = true ] && [ "$ACTION" != ready_for_review ]; then exit 0; fi
        if [ "$tipo" = feature ]; then
          mover "$EXEC" "$n" "CI/PR" "A fazer|Feature|Code|Reprovado|-"
        else
          mover "$BUGS" "$n" "CI/PR" "Novo|Em correção|Reprovado|-"
        fi
        ;;
      closed)
        if [ "${MERGED:-false}" = true ]; then
          # Mesclado na develop -> Homologacao. (Na main, quem cuida e o pos-deploy.)
          # Se nao mexe no executavel (label sem-executavel no PR ou na issue), nao ha o que testar:
          # o cartao vai direto para Aprovado.
          [ "${BASE_REF:-}" = "$DEVELOP" ] || exit 0
          destino="Homologação"
          if [[ ",${PR_LABELS:-}," == *",sem-executavel,"* ]] || \
             gh api "repos/$GITHUB_REPOSITORY/issues/$n" --jq '[.labels[].name] | join(",")' | grep -qw 'sem-executavel'; then
            destino="Aprovado"
          fi
          if [ "$tipo" = feature ]; then
            mover "$EXEC" "$n" "$destino" "A fazer|Feature|Code|CI/PR"
          else
            mover "$BUGS" "$n" "$destino" "Novo|Em correção|CI/PR"
          fi
        else
          # PR fechado sem mesclar -> volta para desenvolvimento.
          if [ "$tipo" = feature ]; then
            mover "$EXEC" "$n" "Code" "CI/PR"
          else
            mover "$BUGS" "$n" "Em correção" "CI/PR"
          fi
        fi
        ;;
    esac
    ;;
esac
