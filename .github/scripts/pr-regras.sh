#!/usr/bin/env bash
# Regras do processo aplicadas a todo PR (chamado por .github/workflows/pr-regras.yml).
#
# Erros (falham a checagem):
#   - origem/destino fora do padrao git flow:
#       feature/<n>-<slug> ou bugfix/<n>-<slug>  ->  develop
#       release/x.y.z ou hotfix/<n>-<slug>       ->  main
#       dependabot/**                            ->  develop (atualizacao de dependencias)
#   - feature/bugfix/hotfix sem referencia a uma issue (#n no branch/titulo/corpo)
# Avisos (nao falham): PR de codigo sem nenhum arquivo de teste alterado.
# Efeito: etiqueta o PR (task para feature, bug para bugfix/hotfix) e marca `sem-executavel` (no PR e
# na issue ligada) quando o diff nao toca o que vai dentro do executavel (ver toca-executavel.sh); se
# depois o PR passar a tocar, a marca e retirada.
#
# Variaveis: HEAD_REF, BASE_REF, PR_TITLE, PR_BODY, PR_NUMBER;
# BRANCH_DEVELOP (develop), BRANCH_MAIN (main).
set -euo pipefail

DEVELOP="${BRANCH_DEVELOP:-develop}"
MAIN="${BRANCH_MAIN:-main}"
head="${HEAD_REF:?}"; base="${BASE_REF:?}"
erros=0
erro() { echo "::error::$*"; erros=$((erros + 1)); }

kind=""
if   [[ "$head" =~ ^feature/[0-9]+-[a-z0-9-]+$ ]]; then kind=feature
elif [[ "$head" =~ ^bugfix/[0-9]+-[a-z0-9-]+$ ]];  then kind=bugfix
elif [[ "$head" =~ ^hotfix/[0-9]+-[a-z0-9-]+$ ]];  then kind=hotfix
elif [[ "$head" =~ ^release/[0-9]+\.[0-9]+\.[0-9]+$ ]]; then kind=release
elif [[ "$head" =~ ^dependabot/ ]]; then kind=dependabot
fi

if [ -z "$kind" ]; then
  erro "Branch '$head' fora do padrao. Use feature/<n>-<slug>, bugfix/<n>-<slug>, release/x.y.z ou hotfix/<n>-<slug>."
else
  case "$kind" in
    feature|bugfix)
      [ "$base" = "$DEVELOP" ] || erro "'$head' deve abrir PR para '$DEVELOP', nao para '$base'." ;;
    release|hotfix)
      [ "$base" = "$MAIN" ] || erro "'$head' deve abrir PR para '$MAIN', nao para '$base'." ;;
    dependabot)
      [ "$base" = "$DEVELOP" ] || erro "PRs do Dependabot devem abrir para '$DEVELOP', nao para '$base'." ;;
  esac
fi

if [ "$base" = "$MAIN" ] && [ "$kind" != release ] && [ "$kind" != hotfix ]; then
  erro "Somente release/* ou hotfix/* podem entrar em '$MAIN'."
fi

case "$kind" in
  feature|bugfix|hotfix)
    if ! grep -qE '#[0-9]+' <<<"$head ${PR_TITLE:-} ${PR_BODY:-}" && ! [[ "$head" =~ /[0-9]+- ]]; then
      erro "Referencie a issue (Refs #n) na descricao do PR."
    fi
    padrao_teste='(^|/)(tests?|__tests__|e2e|spec)/|\.(test|spec)\.[a-z]+$|_test\.[a-z]+$|(^|/)test_[^/]+\.py$'
    if ! gh pr diff "${PR_NUMBER:?}" --name-only | grep -qE "$padrao_teste"; then
      echo "::warning::Nenhum arquivo de teste alterado neste PR. Toda tarefa/bug inclui testes automatizados (ignore apenas em PR de documentacao)."
    fi
    ;;
esac

# Etiqueta por tipo de branch (ajuda as notas de release).
if [ -n "${PR_NUMBER:-}" ]; then
  case "$kind" in
    feature)        gh pr edit "$PR_NUMBER" --add-label task >/dev/null 2>&1 || true ;;
    bugfix|hotfix)  gh pr edit "$PR_NUMBER" --add-label bug  >/dev/null 2>&1 || true ;;
  esac
fi

# `sem-executavel`: docs, testes, workflows e scripts nao entram no .exe, entao nao precisam de
# homologacao nem de release. Em PR de fork o token e somente leitura: falhas sao ignoradas.
if [ -n "${PR_NUMBER:-}" ] && [ "$erros" -eq 0 ] && [[ "$kind" == feature || "$kind" == bugfix || "$kind" == dependabot ]]; then
  issue=""; [[ "$head" =~ ^(feature|bugfix)/([0-9]+)- ]] && issue="${BASH_REMATCH[2]}"
  arquivos=$(gh pr diff "$PR_NUMBER" --name-only 2>/dev/null || true)
  rc=0; printf '%s\n' "$arquivos" | bash "$(dirname "$0")/toca-executavel.sh" || rc=$?
  if [ "$rc" -eq 1 ]; then
    gh pr edit "$PR_NUMBER" --add-label sem-executavel >/dev/null 2>&1 || true
    [ -z "$issue" ] || gh issue edit "$issue" --add-label sem-executavel >/dev/null 2>&1 || true
    echo "PR nao altera o executavel: marcado 'sem-executavel' (dispensa homologacao e release)."
  elif [ "$rc" -eq 0 ]; then
    gh pr edit "$PR_NUMBER" --remove-label sem-executavel >/dev/null 2>&1 || true
    [ -z "$issue" ] || gh issue edit "$issue" --remove-label sem-executavel >/dev/null 2>&1 || true
  fi
fi

[ "$erros" -eq 0 ] || exit 1
echo "PR dentro das regras do processo."
