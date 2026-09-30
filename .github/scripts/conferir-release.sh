#!/usr/bin/env bash
# Portao de publicacao: uma versao so chega a producao se existir uma release candidata
# (vX.Y.Z-rc.N, a homologacao) e se o codigo nao mudou depois dela.
#
# Confere: (1) a versao legivel (versao.sh: src/printroute/version.py); (2) secao "## [X.Y.Z]" no CHANGELOG; (3) existe a tag da
# ultima rc dessa versao; (4) src/, o compilador, o instalador (Inno Setup) e as dependencias de build
# sao identicos aos da rc (o binario/instalador testados sao os que serao publicados).
# Usado pelo CI (PR para a main) e pelo workflow "Publicar release". Grava rc_tag= em GITHUB_OUTPUT.
set -euo pipefail

AQUI="$(cd "$(dirname "$0")" && pwd)"
versao=$(bash "$AQUI/versao.sh")

grep -q "^## \[${versao}\]" CHANGELOG.md || {
  echo "::error::CHANGELOG.md sem a secao '## [${versao}]'."; exit 1; }

rc_tag=$(git tag -l "v${versao}-rc.*" | sort -V | tail -n 1)
[ -n "$rc_tag" ] || {
  echo "::error::Nao existe release candidata (v${versao}-rc.N). Ela e criada pelo workflow 'Build release candidata' quando a branch release/${versao} (ou hotfix/*) recebe um push. Teste a candidata em homologacao antes de publicar."
  exit 1
}

if ! git diff --quiet "$rc_tag" HEAD -- src packaging/windows/build_exe.py packaging/windows/instalador.iss requirements-build.txt; then
  echo "::error::O codigo mudou depois da candidata ${rc_tag}. Envie um push na branch de release para gerar uma nova candidata, teste-a e so entao publique."
  git diff --stat "$rc_tag" HEAD -- src packaging/windows/build_exe.py packaging/windows/instalador.iss requirements-build.txt
  exit 1
fi

echo "Versao ${versao} pronta para producao: candidata ${rc_tag} testada, codigo identico."
echo "rc_tag=${rc_tag}" >> "${GITHUB_OUTPUT:-/dev/null}"
