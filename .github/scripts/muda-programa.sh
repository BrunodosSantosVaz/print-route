#!/usr/bin/env bash
# Le o corpo de um epico (stdin) e imprime a resposta do campo "Muda o programa?" do formulario:
# "sim", "nao" ou vazio (campo ausente ou sem resposta: epicos antigos). Vazio e tratado como
# "muda o programa" pela esteira (o caminho seguro, que exige versao).
# Usado por kanban.sh e iniciar-sprint.sh; testado em tests/test_muda_programa.py.
set -euo pipefail
# O awk le a entrada ATE O FIM (sem "exit" no meio): sair cedo fecha o pipe e, com corpo grande, o
# "tr" antes dele morre com SIGPIPE (exit 141), o que derrubava o Kanban com pipefail.
tr -d '\r' | awk '
  /^###[[:space:]]+/ { dentro = ($0 ~ /^###[[:space:]]+Muda o programa\?[[:space:]]*$/); next }
  dentro && NF && resposta == "" {
    linha = tolower($0)
    if (linha ~ /^[[:space:]]*sim/) resposta = "sim"
    else if (linha ~ /^[[:space:]]*n(ã|a)o/) resposta = "nao"
  }
  END { if (resposta != "") print resposta }'
