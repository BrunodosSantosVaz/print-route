#!/usr/bin/env bash
# Definicoes compartilhadas dos tres paineis: colunas (Status) e funcoes.
# Cada coluna e "Nome:COR" (cores validas do GitHub: GRAY BLUE PURPLE YELLOW
# ORANGE GREEN RED PINK). Para mudar as colunas de um projeto, edite aqui e
# rode scripts/atualizar-colunas.sh.

STATUS_PLANEJAMENTO=(
  "Brainstorm:PURPLE"
  "Backlog:GRAY"
  "Backlog Refinement:YELLOW"
  "Validar protótipo:PINK"
  "Próxima sprint:BLUE"
  "Em desenvolvimento:ORANGE"
  "Concluída:GREEN"
)
STATUS_EXECUCAO=(
  "A fazer:GRAY"
  "Feature:BLUE"
  "Code:BLUE"
  "CI/PR:YELLOW"
  "Homologação:ORANGE"
  "Aprovado:GREEN"
  "Reprovado:RED"
  "Concluído:GREEN"
)
STATUS_BUGS=(
  "Novo:RED"
  "Em correção:BLUE"
  "CI/PR:YELLOW"
  "Homologação:ORANGE"
  "Aprovado:GREEN"
  "Reprovado:RED"
  "Corrigido:GREEN"
)

# definir_status OWNER NUMERO "Nome:COR" ...
# ATENCAO: substitui as opcoes do campo Status. Cartoes que ja estavam em uma
# coluna com o mesmo nome podem perder o valor (o GitHub recria as opcoes);
# rode com o painel vazio ou reclassifique os cartoes depois.
definir_status() {
  local owner="$1" numero="$2"; shift 2
  local campo_id lista="" item nome cor
  campo_id=$(gh project field-list "$numero" --owner "$owner" --format json \
    --jq '.fields[] | select(.name=="Status") | .id')
  for item in "$@"; do
    nome="${item%%:*}"; cor="${item##*:}"
    lista+="{name: \"$nome\", color: $cor, description: \"\"}"
  done
  gh api graphql -f query="
    mutation {
      updateProjectV2Field(input: {
        fieldId: \"$campo_id\",
        singleSelectOptions: [$lista]
      }) { projectV2Field { ... on ProjectV2SingleSelectField { id } } }
    }" >/dev/null
}

# criar_campo_sprint OWNER NUMERO [AAAA-MM-DD]
# Cria o campo "Sprint" (Iteration, 2 semanas) no painel: a sprint e um periodo de trabalho,
# independente de versao (o milestone continua sendo so a versao). Sem data, a primeira sprint
# comeca na segunda-feira da semana atual. Ja existindo, nao faz nada.
criar_campo_sprint() {
  local owner="$1" numero="$2" inicio="${3:-}" projeto_id iteracoes="" i data
  if gh project field-list "$numero" --owner "$owner" --format json --jq '.fields[].name' | grep -qx Sprint; then
    echo "  (campo 'Sprint' ja existe no painel $numero)"; return 0
  fi
  [ -n "$inicio" ] || inicio=$(date -d "-$(( $(date +%u) - 1 )) days" +%F)
  for i in 1 2 3; do
    data=$(date -d "$inicio +$(( (i - 1) * 14 )) days" +%F)
    iteracoes+="{title: \"Sprint $i\", startDate: \"$data\", duration: 14}"
  done
  projeto_id=$(gh project view "$numero" --owner "$owner" --format json --jq '.id')
  gh api graphql -f query="
    mutation {
      createProjectV2Field(input: {
        projectId: \"$projeto_id\", dataType: ITERATION, name: \"Sprint\",
        iterationConfiguration: {startDate: \"$inicio\", duration: 14, iterations: [$iteracoes]}
      }) { projectV2Field { ... on ProjectV2IterationField { id } } }
    }" >/dev/null
  echo "  campo 'Sprint' criado no painel $numero (Sprint 1 comeca em $inicio, 2 semanas cada)"
}

# criar_visoes OWNER NUMERO [roadmap]
# Converte a visao padrao (tabela) em QUADRO (colunas = Status), cria a visao
# "Tabela" e, se pedido, o "Roadmap". Agrupar a tabela por Milestone, limite de
# WIP e workflows continuam sendo passos da interface (docs/processo.md).
criar_visoes() {
  local owner="$1" numero="$2" extra="${3:-}" projeto_id view_id
  projeto_id=$(gh project view "$numero" --owner "$owner" --format json --jq '.id')
  view_id=$(gh api graphql -f query="{ node(id:\"$projeto_id\") { ... on ProjectV2 { views(first:1) { nodes { id } } } } }" \
    --jq '.data.node.views.nodes[0].id')
  gh api graphql -f query="mutation { updateProjectV2View(input:{viewId:\"$view_id\", name:\"Quadro\", layout: BOARD_LAYOUT}) { projectV2View { id } } }" >/dev/null
  gh api graphql -f query="mutation { createProjectV2View(input:{projectId:\"$projeto_id\", name:\"Tabela\", layout: TABLE_LAYOUT}) { projectV2View { id } } }" >/dev/null
  if [ "$extra" = "roadmap" ]; then
    gh api graphql -f query="mutation { createProjectV2View(input:{projectId:\"$projeto_id\", name:\"Roadmap\", layout: ROADMAP_LAYOUT}) { projectV2View { id } } }" >/dev/null
  fi
}

# campos_visiveis OWNER NUMERO "Nome da visao" "Campo1,Campo2,..."
# Define quais campos a visao mostra (cartoes do quadro / colunas da tabela).
campos_visiveis() {
  local owner="$1" numero="$2" visao="$3" campos="$4" json ids view_id
  json=$(gh api graphql -F n="$numero" -f o="$owner" -f query='
    query($o:String!,$n:Int!){ repositoryOwner(login:$o){ ... on ProjectV2Owner { projectV2(number:$n){
      fields(first:40){ nodes{ ... on ProjectV2FieldCommon { id name } } }
      views(first:10){ nodes{ id name } } } } } }')
  view_id=$(jq -r --arg v "$visao" '.data.repositoryOwner.projectV2.views.nodes[] | select(.name==$v) | .id' <<<"$json")
  ids=$(jq -c --arg c "$campos" '[ ($c | split(",")[]) as $n
      | .data.repositoryOwner.projectV2.fields.nodes[] | select(.name==$n) | .id ]' <<<"$json")
  gh api graphql -f query="mutation { updateProjectV2View(input:{viewId:\"$view_id\", configuration:{visibleFieldIds:$ids}}) { projectV2View { id } } }" >/dev/null
}

# Campos de cada visao: a Sprint (periodo de trabalho) aparece em Planejamento e Execucao; o
# Milestone (so versao real) aparece em Execucao e Bugs.
aplicar_campos_visiveis() {
  local o="$1" p="$2" e="$3" b="$4"
  campos_visiveis "$o" "$p" Quadro  "Title,Status,Sprint,Prioridade,Data-alvo,Sub-issues progress"
  campos_visiveis "$o" "$p" Tabela  "Title,Status,Sprint,Prioridade,Data-alvo,Sub-issues progress,Labels"
  campos_visiveis "$o" "$e" Quadro  "Title,Status,Sprint,Milestone,Parent issue,Prioridade,Estimativa,Linked pull requests"
  campos_visiveis "$o" "$e" Tabela  "Title,Status,Sprint,Milestone,Parent issue,Prioridade,Estimativa,Linked pull requests,Labels"
  campos_visiveis "$o" "$b" Quadro  "Title,Status,Milestone,Severidade,Onde,Prioridade,Linked pull requests"
  campos_visiveis "$o" "$b" Tabela  "Title,Status,Milestone,Severidade,Onde,Prioridade,Linked pull requests,Labels"
}
