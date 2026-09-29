#!/usr/bin/env bash
# Configura no GitHub o que as automacoes precisam:
#   - variaveis do repositorio (dono e numeros dos tres paineis);
#   - opcoes de merge (squash e merge commit ligados; NAO apagar branch ao mesclar;
#     auto-merge desligado);
#   - alertas de vulnerabilidade e correcoes automaticas de seguranca.
# O SEGREDO PROJETO_TOKEN (PAT) nao pode ser criado por script: veja docs/processo.md.
#   gh secret set PROJETO_TOKEN --repo OWNER/REPO
#
# Uso: scripts/processo/configurar-automacoes.sh OWNER/REPO N_PLANEJAMENTO N_EXECUCAO N_BUGS
set -euo pipefail

REPO="${1:?Uso: $0 OWNER/REPO N_PLANEJAMENTO N_EXECUCAO N_BUGS}"
N1="${2:?}"; N2="${3:?}"; N3="${4:?}"
OWNER="${REPO%%/*}"

gh variable set PROJETO_OWNER        --repo "$REPO" --body "$OWNER"
gh variable set PROJETO_PLANEJAMENTO --repo "$REPO" --body "$N1"
gh variable set PROJETO_EXECUCAO     --repo "$REPO" --body "$N2"
gh variable set PROJETO_BUGS         --repo "$REPO" --body "$N3"
echo "variaveis ok"

gh api -X PATCH "repos/$REPO" \
  -F allow_squash_merge=true -F allow_merge_commit=true \
  -F delete_branch_on_merge=false -F allow_auto_merge=false >/dev/null
echo "opcoes de merge ok"

gh api -X PUT "repos/$REPO/vulnerability-alerts" >/dev/null 2>&1 && echo "alertas de vulnerabilidade ok" || echo "(alertas: nao disponivel)"
gh api -X PUT "repos/$REPO/automated-security-fixes" >/dev/null 2>&1 && echo "correcoes automaticas ok" || echo "(correcoes automaticas: nao disponivel)"

echo
echo "Falta o segredo: gh secret set PROJETO_TOKEN --repo $REPO   (cole o PAT quando pedir)"
