#!/usr/bin/env bash
# PrintRoute: decide se uma lista de arquivos (stdin, um caminho por linha) altera o que vai DENTRO do executavel:
# o codigo do programa (src/) ou as dependencias empacotadas (requirements-build.txt).
# Saida 0 = toca o executavel; 1 = nao toca (docs, testes, workflows, scripts, exemplos...);
# 2 = lista vazia (sem informacao). Fonte unica da regra "sem-executavel" (pr-regras.sh); a acao
# "Publicar sem executavel" usa o mesmo criterio com git diff (src e requirements-build.txt).
set -euo pipefail
tem=0; toca=0
while IFS= read -r arquivo; do
  [ -n "$arquivo" ] || continue
  tem=1
  if [[ "$arquivo" == src/* || "$arquivo" == requirements-build.txt ]]; then toca=1; fi
done
[ "$tem" -eq 1 ] || exit 2
[ "$toca" -eq 1 ] && exit 0 || exit 1
