#!/usr/bin/env bash
# Auxiliar dos workflows: mover cartoes nos paineis (GitHub Projects v2).
#
# Subcomandos:
#   projeto.sh mover  <painel> <issue> "<Status>" ["<De1|De2>"]
#       Adiciona a issue ao painel (se nao estiver) e define o Status.
#       Com o 4o argumento, so move se o Status ATUAL estiver na lista
#       (use "-" para "sem status"); evita mandar o cartao para tras.
#   projeto.sh cartoes <painel> "<Status>"
#       Imprime os numeros das issues deste repositorio que estao no Status.
#   projeto.sh remover <painel> <issue>
#       Tira a issue do painel.
#   projeto.sh sprint <painel> <issue> ["<Sprint N>"|atual]
#       Poe a issue na Sprint (campo Iteration "Sprint") indicada; padrao: a sprint atual.
#   projeto.sh sprint-atual <painel>
#       Imprime o titulo da sprint atual (vazio se hoje nao cai em nenhuma).
#   projeto.sh sprint-de <painel> <issue>
#       Imprime o titulo da sprint da issue (vazio se nao tem).
#   A sprint e o periodo de trabalho, independente de versao (o milestone e so a versao).
#   HOJE=AAAA-MM-DD muda o "hoje" (testes).
#
# Ambiente: GH_TOKEN (com escopo "project"), PROJETO_OWNER (dono dos paineis),
# GITHUB_REPOSITORY (owner/repo). <painel> e o NUMERO do projeto.
# DRY_RUN=1 apenas imprime o que faria (nao altera nada).
set -euo pipefail

: "${PROJETO_OWNER:?defina PROJETO_OWNER}"
: "${GITHUB_REPOSITORY:?defina GITHUB_REPOSITORY}"

projeto_id() {
  gh api graphql -F n="$1" -f o="$PROJETO_OWNER" -f query='
    query($o:String!,$n:Int!){ repositoryOwner(login:$o){
      ... on ProjectV2Owner { projectV2(number:$n){ id } } } }' \
    --jq '.data.repositoryOwner.projectV2.id'
}

# imprime: <id-do-campo-Status>\t<id-da-opcao>  (para o Status pedido)
status_ids() {
  gh api graphql -F n="$1" -f o="$PROJETO_OWNER" -f query='
    query($o:String!,$n:Int!){ repositoryOwner(login:$o){
      ... on ProjectV2Owner { projectV2(number:$n){
        field(name:"Status"){ ... on ProjectV2SingleSelectField { id options{ id name } } } } } } }' \
  | jq -r --arg s "$2" '.data.repositoryOwner.projectV2.field as $f
      | ($f.options[] | select(.name==$s) | .id) as $o | "\($f.id)\t\($o)"'
}

mover() {
  local painel="$1" issue="$2" destino="$3" de="${4:-}"
  local pid node item atual ids campo opcao
  if [ "${DRY_RUN:-}" = 1 ]; then
    echo "[simulado] painel $painel: #$issue -> '$destino' (somente de: ${de:-qualquer})"
    return 0
  fi
  pid=$(projeto_id "$painel")
  node=$(gh api "repos/$GITHUB_REPOSITORY/issues/$issue" --jq '.node_id')
  item=$(gh api graphql -f p="$pid" -f c="$node" -f query='
    mutation($p:ID!,$c:ID!){ addProjectV2ItemById(input:{projectId:$p, contentId:$c}){ item{ id } } }' \
    --jq '.data.addProjectV2ItemById.item.id')
  atual=$(gh api graphql -f i="$item" -f query='
    query($i:ID!){ node(id:$i){ ... on ProjectV2Item {
      fieldValueByName(name:"Status"){ ... on ProjectV2ItemFieldSingleSelectValue { name } } } } }' \
    --jq '.data.node.fieldValueByName.name // "-"')
  if [ -n "$de" ] && ! printf '%s' "|$de|" | grep -qF "|$atual|"; then
    echo "#$issue no painel $painel: '$atual' fora de [$de]; mantido."
    return 0
  fi
  if [ "$atual" = "$destino" ]; then
    echo "#$issue no painel $painel: ja esta em '$destino'."
    return 0
  fi
  ids=$(status_ids "$painel" "$destino")
  campo="${ids%%$'\t'*}"; opcao="${ids##*$'\t'}"
  if [ -z "$opcao" ] || [ "$opcao" = "$ids" ]; then
    echo "Status '$destino' nao existe no painel $painel." >&2; return 1
  fi
  gh api graphql -f p="$pid" -f i="$item" -f f="$campo" -f o="$opcao" -f query='
    mutation($p:ID!,$i:ID!,$f:ID!,$o:String!){ updateProjectV2ItemFieldValue(input:{
      projectId:$p, itemId:$i, fieldId:$f, value:{singleSelectOptionId:$o}}){ projectV2Item{ id } } }' >/dev/null
  echo "#$issue no painel $painel: '$atual' -> '$destino'."
}

# imprime: <id-do-campo-Sprint>\t<id-da-iteracao>\t<titulo>  ("atual" = a que contem HOJE)
iteracao() {
  local painel="$1" alvo="${2:-atual}" hoje="${HOJE:-$(date +%F)}"
  gh api graphql -F n="$painel" -f o="$PROJETO_OWNER" -f query='
    query($o:String!,$n:Int!){ repositoryOwner(login:$o){
      ... on ProjectV2Owner { projectV2(number:$n){
        field(name:"Sprint"){ ... on ProjectV2IterationField { id configuration{
          iterations{ id title startDate duration } } } } } } } }' \
  | jq -r --arg a "$alvo" --arg h "$hoje" '.data.repositoryOwner.projectV2.field as $f
      | ($f.configuration.iterations // [])[]
      | select(if $a == "atual" then
          (.startDate <= $h and $h < ((.startDate + "T00:00:00Z" | fromdateiso8601) + .duration * 86400
                                     | strftime("%Y-%m-%d")))
        else .title == $a end)
      | "\($f.id)\t\(.id)\t\(.title)"' | head -n 1
}

item_de() {
  local pid="$1" issue="$2" node
  node=$(gh api "repos/$GITHUB_REPOSITORY/issues/$issue" --jq '.node_id')
  gh api graphql -f p="$pid" -f c="$node" -f query='
    mutation($p:ID!,$c:ID!){ addProjectV2ItemById(input:{projectId:$p, contentId:$c}){ item{ id } } }' \
    --jq '.data.addProjectV2ItemById.item.id'
}

sprint() {
  local painel="$1" issue="$2" alvo="${3:-atual}" linha campo it titulo pid item
  linha=$(iteracao "$painel" "$alvo")
  if [ -z "$linha" ]; then
    echo "Sprint '$alvo' nao encontrada no painel $painel (o campo 'Sprint' existe? veja scripts/processo/criar-campo-sprint.sh)." >&2
    return 1
  fi
  IFS=$'\t' read -r campo it titulo <<<"$linha"
  if [ "${DRY_RUN:-}" = 1 ]; then echo "[simulado] painel $painel: #$issue -> Sprint '$titulo'"; return 0; fi
  pid=$(projeto_id "$painel")
  item=$(item_de "$pid" "$issue")
  gh api graphql -f p="$pid" -f i="$item" -f f="$campo" -f t="$it" -f query='
    mutation($p:ID!,$i:ID!,$f:ID!,$t:String!){ updateProjectV2ItemFieldValue(input:{
      projectId:$p, itemId:$i, fieldId:$f, value:{iterationId:$t}}){ projectV2Item{ id } } }' >/dev/null
  echo "#$issue no painel $painel: Sprint '$titulo'."
}

sprint_atual() {
  local linha; linha=$(iteracao "$1" atual)
  [ -z "$linha" ] || printf '%s\n' "${linha##*$'\t'}"
}

sprint_de() {
  local painel="$1" issue="$2" pid item
  pid=$(projeto_id "$painel")
  item=$(item_de "$pid" "$issue")
  gh api graphql -f i="$item" -f query='
    query($i:ID!){ node(id:$i){ ... on ProjectV2Item {
      fieldValueByName(name:"Sprint"){ ... on ProjectV2ItemFieldIterationValue { title } } } } }' \
    --jq '.data.node.fieldValueByName.title // empty'
}

cartoes() {
  local painel="$1" status="$2" pid
  pid=$(projeto_id "$painel")
  gh api graphql --paginate -f id="$pid" -f query='
    query($id:ID!,$endCursor:String){ node(id:$id){ ... on ProjectV2 {
      items(first:100, after:$endCursor){ pageInfo{ hasNextPage endCursor } nodes{
        fieldValueByName(name:"Status"){ ... on ProjectV2ItemFieldSingleSelectValue { name } }
        content{ ... on Issue { number repository{ nameWithOwner } } } } } } } }' \
    --jq ".data.node.items.nodes[]
      | select(.fieldValueByName.name==\"$status\" and .content.repository.nameWithOwner==\"$GITHUB_REPOSITORY\")
      | .content.number"
}

remover() {
  local painel="$1" issue="$2" pid node item
  if [ "${DRY_RUN:-}" = 1 ]; then echo "[simulado] remover #$issue do painel $painel"; return 0; fi
  pid=$(projeto_id "$painel")
  node=$(gh api "repos/$GITHUB_REPOSITORY/issues/$issue" --jq '.node_id')
  item=$(gh api graphql -f p="$pid" -f c="$node" -f query='
    mutation($p:ID!,$c:ID!){ addProjectV2ItemById(input:{projectId:$p, contentId:$c}){ item{ id } } }' \
    --jq '.data.addProjectV2ItemById.item.id')
  gh api graphql -f p="$pid" -f i="$item" -f query='
    mutation($p:ID!,$i:ID!){ deleteProjectV2Item(input:{projectId:$p, itemId:$i}){ deletedItemId } }' >/dev/null
  echo "#$issue removida do painel $painel."
}

cmd="${1:-}"; shift || true
case "$cmd" in
  mover)   mover "$@" ;;
  cartoes) cartoes "$@" ;;
  remover) remover "$@" ;;
  sprint)  sprint "$@" ;;
  sprint-atual) sprint_atual "$@" ;;
  sprint-de) sprint_de "$@" ;;
  *) sed -n '2,26p' "$0"; exit 2 ;;
esac
