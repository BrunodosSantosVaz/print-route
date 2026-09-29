#!/usr/bin/env bash
# Apaga a branch release/x.y.z de uma versao JA PUBLICADA, so quando nada se perde. Padrao GitFlow: a
# branch de release e temporaria; o historico da versao fica na TAG vX.Y.Z e na GitHub Release.
# Chamado no fim do encerramento (encerrar-sprint.sh) e usado a mao para limpar branches antigas.
#
# TRAVAS (todas precisam passar; se uma falhar, a branch FICA e sai um aviso, sem erro):
#   1. nome exato release/<x.y.z> (semver); nada de curingas;
#   2. a tag de producao vX.Y.Z existe (a da candidata -rc.N nao conta);
#   3. a GitHub Release vX.Y.Z existe (a versao foi publicada);
#   4. a branch esta contida na tag (compare tag...branch: ahead_by == 0): nenhum commit fica de fora;
#   5. a branch esta contida na main (ahead_by == 0): foi mesclada.
# Tags NUNCA sao apagadas nem movidas: a unica escrita e DELETE git/refs/heads/release/<x.y.z>.
# Idempotente: branch que ja nao existe so gera um aviso.
#
# Voltar a uma versao antiga depois disso: pela tag (git switch --detach vX.Y.Z; veja docs/processo.md).
#
# Variaveis: VERSAO (v0.2.0 ou 0.2.0), SIMULAR=true (so mostra), GITHUB_REPOSITORY, BRANCH_MAIN (main).
set -euo pipefail

R="${GITHUB_REPOSITORY:?}"
MAIN="${BRANCH_MAIN:-main}"
v="${VERSAO:?informe a versao}"; v="${v#v}"
SIMULAR="${SIMULAR:-false}"

# trava 1: so release/<x.y.z>
if ! [[ "$v" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "::error::Versao '$v' invalida (use x.y.z). Nada foi apagado."; exit 2
fi
tag="v$v"; branch="release/$v"
manter() { echo "::warning::$branch mantida: $1."; exit 0; }

if ! gh api "repos/$R/git/ref/heads/$branch" >/dev/null 2>&1; then
  echo "Branch $branch ja nao existe: nada a apagar."; exit 0
fi
sufixo=""; [ "$SIMULAR" != true ] || sufixo=" [SIMULACAO]"
echo "Conferindo $branch antes de apagar${sufixo}:"

# trava 2: tag de producao
gh api "repos/$R/git/ref/tags/$tag" >/dev/null 2>&1 || manter "a tag $tag nao existe"
echo "  ok: a tag $tag existe"

# trava 3: versao publicada
gh release view "$tag" --repo "$R" >/dev/null 2>&1 || manter "a Release $tag nao existe (versao nao publicada)"
echo "  ok: a Release $tag existe"

# trava 4: nada da branch fica fora da tag
fora_tag=$(gh api "repos/$R/compare/$tag...$branch" --jq '.ahead_by' 2>/dev/null || echo "?")
[ "$fora_tag" = 0 ] || manter "$fora_tag commit(s) da branch nao estao na tag $tag"
echo "  ok: todo commit da branch esta na tag $tag"

# trava 5: mesclada na main
fora_main=$(gh api "repos/$R/compare/$MAIN...$branch" --jq '.ahead_by' 2>/dev/null || echo "?")
[ "$fora_main" = 0 ] || manter "$fora_main commit(s) da branch nao estao na $MAIN"
echo "  ok: a branch esta contida na $MAIN"

if [ "$SIMULAR" = true ]; then
  echo "[simulado] apagar $branch (a versao continua na tag $tag e na Release)"
else
  gh api -X DELETE "repos/$R/git/refs/heads/$branch" >/dev/null
  echo "Branch apagada: $branch (a versao continua na tag $tag e na Release)."
fi
