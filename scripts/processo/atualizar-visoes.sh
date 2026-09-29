#!/usr/bin/env bash
# Reaplica os campos visiveis das visoes (Quadro/Tabela) nos tres paineis.
# Uso: scripts/atualizar-visoes.sh OWNER N_PLANEJAMENTO N_EXECUCAO N_BUGS
set -euo pipefail
OWNER="${1:?Uso: $0 OWNER N_PLANEJAMENTO N_EXECUCAO N_BUGS}"
# shellcheck source=lib-paineis.sh
source "$(dirname "$0")/lib-paineis.sh"
aplicar_campos_visiveis "$OWNER" "${2:?}" "${3:?}" "${4:?}"
echo "campos visiveis atualizados"
