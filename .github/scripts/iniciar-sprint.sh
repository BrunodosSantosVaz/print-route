#!/usr/bin/env bash
# "Iniciar sprint": move os epicos de "Proxima sprint" para "Em desenvolvimento", poe o epico e as
# tarefas na Sprint (campo Iteration dos paineis: o periodo de trabalho) e cria, para cada epico, as
# tarefas da secao "Tarefas previstas" do corpo: sub-issues label "task", com cartao em "A fazer" no
# painel de Execucao. Epico SEM tarefas previstas nao e movido (fica em "Proxima sprint" com um
# aviso). Idempotente: tarefas ja criadas (mesmo titulo, como sub-issue do epico) nao se repetem,
# e se o milestone ja existe ele e reaproveitado.
#
# SPRINT x VERSAO (padrao do mercado: sprint nao e release):
#   - epico que MUDA o programa (sem a label `sem-executavel`): tarefas no milestone da VERSAO,
#     que entao e obrigatoria; o milestone e criado se nao existir;
#   - epico `sem-executavel` (docs, testes, esteira, compilador): tarefas com a label
#     `sem-executavel` e SEM milestone. Sprint so com esses epicos nao precisa de versao e nao cria
#     milestone nenhum (nada sera compilado nem versionado).
#
# Os criterios de aceite e os testes de cada tarefa saem como esqueleto para preencher no
# refinamento (ver docs/processo.md).
#
# Variaveis: VERSAO (v0.6.0; opcional se todos os epicos forem sem-executavel), DATA (opcional,
# AAAA-MM-DD), SPRINT (opcional: titulo da iteracao; padrao a sprint atual), SIMULAR=true,
# PROJETO_PLANEJAMENTO, PROJETO_EXECUCAO.
set -euo pipefail

AQUI="$(cd "$(dirname "$0")" && pwd)"
PLAN="${PROJETO_PLANEJAMENTO:?}"; EXEC="${PROJETO_EXECUCAO:?}"
R="$GITHUB_REPOSITORY"; OWNER="${R%%/*}"; REPO="${R##*/}"
v="${VERSAO:-}"; v="${v#v}"; tag="${v:+v$v}"
DATA="${DATA:-}"
SIMULAR="${SIMULAR:-false}"
[ "$SIMULAR" = true ] && export DRY_RUN=1
projeto() { bash "$AQUI/projeto.sh" "$@"; }
gql() { gh api graphql -H "GraphQL-Features: sub_issues" "$@"; }

if [ -n "$v" ] && ! [[ "$v" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "::error::Versao '$v' invalida (use x.y.z)."; exit 1
fi
if [ -n "$DATA" ] && ! [[ "$DATA" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
  echo "::error::Data '$DATA' invalida (use AAAA-MM-DD)."; exit 1
fi

# ---- epicos da proxima sprint, as tarefas previstas de cada um e se mudam o programa
mapfile -t epicos < <(projeto cartoes "$PLAN" "Próxima sprint")
milestone=""
if [ -n "$tag" ]; then
  milestone=$(gh api "repos/$R/milestones?state=all&per_page=100" --paginate \
    --jq ".[] | select(.title==\"$tag\") | .number" | head -1)
fi
if [ "${#epicos[@]}" -eq 0 ]; then
  if [ -n "$milestone" ]; then echo "Milestone $tag ja existe e nao ha epicos em 'Próxima sprint'; nada a fazer."; exit 0; fi
  echo "::error::Nenhum epico na coluna 'Próxima sprint'. Escolha os epicos da sprint antes de iniciar."; exit 1
fi

iniciar=(); sem_tarefas=(); mudam=(); descricao_epicos=""
declare -A titulo_epico sem_exe
for n in "${epicos[@]}"; do
  titulo_epico[$n]=$(gh api "repos/$R/issues/$n" --jq .title)
  sem_exe[$n]=$(gh api "repos/$R/issues/$n" --jq '[.labels[].name] | index("sem-executavel") != null')
  qtd=$(gh api "repos/$R/issues/$n" --jq '.body // ""' | bash "$AQUI/tarefas-do-epico.sh" | wc -l)
  if [ "$qtd" -eq 0 ]; then
    sem_tarefas+=("$n")
  else
    iniciar+=("$n")
    if [ "${sem_exe[$n]}" != true ]; then mudam+=("$n"); descricao_epicos+="- #$n ${titulo_epico[$n]}"$'\n'; fi
  fi
done
for n in "${sem_tarefas[@]:-}"; do
  [ -n "$n" ] || continue
  echo "::warning::Epico #$n (${titulo_epico[$n]}) nao tem a secao 'Tarefas previstas' com itens: continua em 'Próxima sprint'. Liste as tarefas no corpo do epico e rode de novo."
done
if [ "${#iniciar[@]}" -eq 0 ]; then
  echo "::error::Nenhum epico de 'Próxima sprint' tem 'Tarefas previstas'. Nada foi iniciado."; exit 1
fi

# ---- versao: so para os epicos que mudam o programa
if [ "${#mudam[@]}" -gt 0 ] && [ -z "$tag" ]; then
  echo "::error::Os epicos ${mudam[*]/#/#} mudam o programa (nao tem a label sem-executavel) e precisam de uma versao: rode com versao=vX.Y.Z. Se algum deles nao mexe em src/ nem em requirements-build.txt, ponha a label sem-executavel nele. Nada foi iniciado."
  exit 1
fi
if [ "${#mudam[@]}" -eq 0 ] && [ -n "$tag" ]; then
  echo "::warning::Nenhum epico da sprint muda o programa (todos sem-executavel): a versao $tag foi ignorada e nenhum milestone e criado."
  tag=""; milestone=""
fi

# ---- milestone (so se algum epico muda o programa; cria se nao existe)
if [ -n "$tag" ] && [ -z "$milestone" ]; then
  descricao="Versão $tag

Épicos:
$descricao_epicos"
  args=(-f "title=$tag" -f "description=$descricao")
  [ -z "$DATA" ] || args+=(-f "due_on=${DATA}T12:00:00Z")
  if [ "$SIMULAR" = true ]; then
    echo "[simulado] criar milestone $tag com os epicos: ${mudam[*]}"
  else
    milestone=$(gh api -X POST "repos/$R/milestones" "${args[@]}" --jq .number)
    echo "Milestone criado: $tag (#$milestone)"
  fi
elif [ -n "$tag" ]; then
  echo "Milestone $tag ja existe (#$milestone); reaproveitado."
fi

# ---- sprint (campo Iteration): a indicada ou a atual; sem o campo, segue sem marcar
sprint="${SPRINT:-$(projeto sprint-atual "$EXEC" 2>/dev/null || true)}"
if [ -z "$sprint" ]; then
  echo "::warning::Nenhuma Sprint atual no painel $EXEC (campo 'Sprint' ausente ou sem iteracao para hoje): epicos e tarefas ficam sem Sprint. Veja scripts/processo/criar-campo-sprint.sh."
fi
marcar_sprint() { [ -z "$sprint" ] || projeto sprint "$1" "$2" "$sprint" >/dev/null || true; }

# ---- para cada epico: cria as tarefas (sub-issues) e move o epico
for n in "${iniciar[@]}"; do
  if [ "${sem_exe[$n]}" = true ]; then destino="sem versao, sem-executavel"; else destino="$tag"; fi
  echo "== Epico #$n: ${titulo_epico[$n]} ($destino)"
  epico_node=$(gh api "repos/$R/issues/$n" --jq .node_id)
  existentes=$(gql -f o="$OWNER" -f r="$REPO" -F n="$n" -f query='
    query($o:String!,$r:String!,$n:Int!){ repository(owner:$o,name:$r){ issue(number:$n){
      subIssues(first:100){ nodes{ title } } } } }' --jq '.data.repository.issue.subIssues.nodes[].title')
  while IFS= read -r tarefa; do
    [ -n "$tarefa" ] || continue
    if grep -qxF -- "$tarefa" <<<"$existentes"; then
      echo "  ja existe: $tarefa"; continue
    fi
    if [ "$SIMULAR" = true ]; then
      echo "  [simulado] criar tarefa '$tarefa' (task, $destino, sub-issue de #$n, cartao em 'A fazer', Sprint '${sprint:--}')"; continue
    fi
    corpo="### Épico
#$n — ${titulo_epico[$n]}

### O que fazer
$tarefa

### Critérios de aceite
- [ ]
- [ ]

### Testes automatizados (obrigatório)
- [ ] Unitário:
- [ ] Integração:

### Impacto
Detalhar ao refinar a tarefa."
    if [ "${sem_exe[$n]}" = true ]; then
      url=$(gh issue create --repo "$R" --title "$tarefa" --label task --label sem-executavel --body "$corpo")
    else
      url=$(gh issue create --repo "$R" --title "$tarefa" --label task --milestone "$tag" --body "$corpo")
    fi
    num="${url##*/}"
    tarefa_node=$(gh api "repos/$R/issues/$num" --jq .node_id)
    gql -f e="$epico_node" -f t="$tarefa_node" -f query='
      mutation($e:ID!,$t:ID!){ addSubIssue(input:{issueId:$e, subIssueId:$t}){ issue{ number } } }' >/dev/null
    projeto mover "$EXEC" "$num" "A fazer" "-" >/dev/null
    marcar_sprint "$EXEC" "$num"
    echo "  criada #$num: $tarefa"
  done < <(gh api "repos/$R/issues/$n" --jq '.body // ""' | bash "$AQUI/tarefas-do-epico.sh")
  marcar_sprint "$PLAN" "$n"
  projeto mover "$PLAN" "$n" "Em desenvolvimento" "Próxima sprint"
done

if [ -n "$tag" ]; then sufixo=", versao $tag"; else sufixo=" (sem versao: nada sera compilado)"; fi
echo "Sprint ${sprint:-(sem Sprint)} iniciada: ${#iniciar[@]} epico(s) em desenvolvimento${sufixo}."
[ "${#sem_tarefas[@]}" -eq 0 ] || echo "Epicos que ficaram em 'Próxima sprint' por falta de 'Tarefas previstas': ${sem_tarefas[*]}"
echo "Proximo passo: refinar as tarefas (criterios de aceite e testes) e rodar a acao 'Criar branches das tarefas' para abrir as branches e mover os cartoes para Feature."
