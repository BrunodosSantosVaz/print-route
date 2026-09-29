#!/usr/bin/env bash
# Reaplica as colunas (Status) definidas em lib-paineis.sh nos tres paineis
# ja existentes.
# Uso: scripts/atualizar-colunas.sh OWNER N_PLANEJAMENTO N_EXECUCAO N_BUGS
set -euo pipefail
OWNER="${1:?Uso: $0 OWNER N_PLANEJAMENTO N_EXECUCAO N_BUGS}"
N1="${2:?}"; N2="${3:?}"; N3="${4:?}"
# shellcheck source=lib-paineis.sh
source "$(dirname "$0")/lib-paineis.sh"

definir_status "$OWNER" "$N1" "${STATUS_PLANEJAMENTO[@]}"; echo "Planejamento (#$N1) ok"
definir_status "$OWNER" "$N2" "${STATUS_EXECUCAO[@]}";     echo "Execucao (#$N2) ok"
definir_status "$OWNER" "$N3" "${STATUS_BUGS[@]}";         echo "Bugs (#$N3) ok"
