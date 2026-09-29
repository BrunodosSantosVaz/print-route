#!/usr/bin/env bash
# Cria o campo "Sprint" (Iteration, 2 semanas) nos paineis Planejamento e Execucao ja existentes
# (paineis novos ja nascem com ele: criar-paineis.sh) e mostra a Sprint nas visoes.
# A sprint e um periodo de trabalho, com ou sem versao; o milestone continua sendo so a versao.
#
# Uso: scripts/processo/criar-campo-sprint.sh OWNER N_PLANEJAMENTO N_EXECUCAO N_BUGS [AAAA-MM-DD]
#      (a data e o inicio da Sprint 1; padrao: segunda-feira da semana atual)
set -euo pipefail
OWNER="${1:?Uso: $0 OWNER N_PLANEJAMENTO N_EXECUCAO N_BUGS [AAAA-MM-DD]}"
P="${2:?}" E="${3:?}" B="${4:?}" INICIO="${5:-}"
# shellcheck source=lib-paineis.sh
source "$(dirname "$0")/lib-paineis.sh"
criar_campo_sprint "$OWNER" "$P" "$INICIO"
criar_campo_sprint "$OWNER" "$E" "$INICIO"
aplicar_campos_visiveis "$OWNER" "$P" "$E" "$B"
echo "Sprint pronta. Novas iteracoes: Configuracoes do painel > Sprint (ou o GitHub acrescenta as proximas)."
