#!/usr/bin/env bash
# PrintRoute: decide se uma lista de arquivos (stdin, um caminho por linha) altera o que vai DENTRO do executavel:
# o codigo do programa (src/), o compilador/empacotador (packaging/windows/build_exe.py,
# packaging/windows/instalador.iss) ou as dependencias empacotadas (requirements-build.txt).
# Saida 0 = toca o executavel; 1 = nao toca (docs, testes, workflows, scripts, exemplos...);
# 2 = lista vazia (sem informacao). Fonte unica da regra "sem-executavel" (pr-regras.sh); a acao
# "Publicar sem executavel" e o "conferir-release.sh" usam o mesmo criterio com git diff.
#
# Bug real (tarefa #24): antes so listava "src/" e "requirements-build.txt" -- um PR que so
# mexia em packaging/windows/build_exe.py (o compilador em si) era marcado "sem-executavel" e
# pulava a homologacao inteira, mesmo mudando o .exe de verdade.
set -euo pipefail
tem=0; toca=0
while IFS= read -r arquivo; do
  [ -n "$arquivo" ] || continue
  tem=1
  case "$arquivo" in
    src/*|requirements-build.txt|packaging/windows/build_exe.py|packaging/windows/instalador.iss) toca=1 ;;
  esac
done
[ "$tem" -eq 1 ] || exit 2
[ "$toca" -eq 1 ] && exit 0 || exit 1
