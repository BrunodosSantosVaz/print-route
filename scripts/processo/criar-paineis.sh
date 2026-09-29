#!/usr/bin/env bash
# Cria os tres paineis (GitHub Projects v2) do processo e liga ao repositorio:
#   "<Produto> — Planejamento", "<Produto> — Execução", "<Produto> — Bugs".
# Configura o campo Status (colunas) e os campos extras de cada painel, inclusive a
# Sprint (Iteration) em Planejamento e Execucao.
# Cria as visoes (Quadro por Status, Tabela e, no Planejamento, Roadmap).
# Os WORKFLOWS (auto-add, item closed), o limite de WIP e o agrupamento da
# tabela so existem na interface web: veja docs/processo.md.
#
# Requisitos: gh CLI autenticada com o escopo "project":
#   gh auth refresh -s project
#
# Uso: scripts/processo/criar-paineis.sh OWNER/REPO "Nome do Produto"
set -euo pipefail

REPO="${1:?Uso: $0 OWNER/REPO \"Nome do Produto\"}"
PRODUTO="${2:?Uso: $0 OWNER/REPO \"Nome do Produto\"}"
OWNER="${REPO%%/*}"

# shellcheck source=lib-paineis.sh
source "$(dirname "$0")/lib-paineis.sh"

# Cria campo de selecao unica (ignora se ja existir).
campo_selecao() {
  local numero="$1" nome="$2" opcoes="$3"
  gh project field-create "$numero" --owner "$OWNER" --name "$nome" \
    --data-type SINGLE_SELECT --single-select-options "$opcoes" >/dev/null 2>&1 \
    || echo "  (campo '$nome' ja existe ou nao pode ser criado)"
}

criar_painel() {
  local titulo="$1"
  local numero
  numero=$(gh project create --owner "$OWNER" --title "$titulo" --format json --jq '.number')
  gh project link "$numero" --owner "$OWNER" --repo "$REPO" >/dev/null
  echo "$numero"
}

echo "== Planejamento =="
N1=$(criar_painel "$PRODUTO — Planejamento")
definir_status "$OWNER" "$N1" "${STATUS_PLANEJAMENTO[@]}"
criar_visoes "$OWNER" "$N1" roadmap
campo_selecao "$N1" "Prioridade" "Alta,Média,Baixa"
gh project field-create "$N1" --owner "$OWNER" --name "Data-alvo" --data-type DATE >/dev/null 2>&1 || true
criar_campo_sprint "$OWNER" "$N1"

echo "== Execução =="
N2=$(criar_painel "$PRODUTO — Execução")
definir_status "$OWNER" "$N2" "${STATUS_EXECUCAO[@]}"
criar_visoes "$OWNER" "$N2"
campo_selecao "$N2" "Prioridade" "Alta,Média,Baixa"
campo_selecao "$N2" "Estimativa" "P,M,G"
criar_campo_sprint "$OWNER" "$N2"

echo "== Bugs =="
N3=$(criar_painel "$PRODUTO — Bugs")
definir_status "$OWNER" "$N3" "${STATUS_BUGS[@]}"
criar_visoes "$OWNER" "$N3"
campo_selecao "$N3" "Severidade" "Crítico,Alto,Médio,Baixo"
campo_selecao "$N3" "Onde" "Homologação,Produção"
campo_selecao "$N3" "Prioridade" "Alta,Média,Baixa"

aplicar_campos_visiveis "$OWNER" "$N1" "$N2" "$N3"

echo
echo "Paineis criados para $REPO:"
for n in "$N1" "$N2" "$N3"; do
  gh project view "$n" --owner "$OWNER" --format json --jq '"  #\(.number) \(.title) — \(.url)"'
done
echo
echo "Falta (somente pela interface): workflows, limite de WIP e agrupamentos."
echo "Veja docs/processo.md."
