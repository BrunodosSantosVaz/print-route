#!/usr/bin/env bash
# Le o corpo de um epico (stdin) e imprime, uma por linha, as tarefas da secao
# "Tarefas previstas" (itens "- [ ] Titulo", "- Titulo" ou "1. Titulo").
# Usado por iniciar-sprint.sh; testado em tests/test_tarefas_do_epico.py.
set -euo pipefail
tr -d '\r' | awk '
  /^###[[:space:]]+/ { dentro = ($0 ~ /^###[[:space:]]+Tarefas previstas[[:space:]]*$/); next }
  dentro && /^[[:space:]]*([-*]|[0-9]+\.)[[:space:]]+/ {
    linha = $0
    sub(/^[[:space:]]*([-*]|[0-9]+\.)[[:space:]]+/, "", linha)
    sub(/^\[[ xX]\][[:space:]]*/, "", linha)
    sub(/[[:space:]]+$/, "", linha)
    if (linha != "") print linha
  }'
