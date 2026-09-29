#!/usr/bin/env bash
# Anuncia a versao publicada na categoria "Anuncios" do Discussions (usa notas.md gerado por
# promover-release.sh). Nunca desfaz uma publicacao: se falhar, so avisa. Variaveis: TAG, GH_TOKEN.
set -uo pipefail
tag="${TAG:?}"; repo="${GITHUB_REPOSITORY:?}"; dono="${repo%%/*}"; nome="${repo##*/}"
ids=$(gh api graphql -f o="$dono" -f n="$nome" -f query='
  query($o:String!,$n:String!){ repository(owner:$o,name:$n){ id
    discussionCategory(slug:"announcements"){ id } } }' \
  --jq '.data.repository | "\(.id) \(.discussionCategory.id)"') || { echo "::warning::Nao consegui ler as categorias do Discussions."; exit 0; }
repo_id="${ids% *}"; cat_id="${ids#* }"
{
  echo "A versão **${tag}** do PrintRoute foi publicada. **[Baixar e ver as notas](https://github.com/${repo}/releases/tag/${tag})**"
  echo
  [ ! -f notas.md ] || cat notas.md
  echo
  echo "---"
  echo "Dúvidas ou ideias? Use o **Q&A** e o **Ideas** aqui no Discussions. Para bugs, abra uma [issue](https://github.com/${repo}/issues/new/choose)."
} > anuncio.md
gh api graphql -f r="$repo_id" -f c="$cat_id" -f t="PrintRoute ${tag} publicada" -f b="$(cat anuncio.md)" -f query='
  mutation($r:ID!,$c:ID!,$t:String!,$b:String!){ createDiscussion(input:{repositoryId:$r, categoryId:$c, title:$t, body:$b}){ discussion{ url } } }' \
  --jq '.data.createDiscussion.discussion.url' || echo "::warning::Nao consegui anunciar no Discussions (a Release ${tag} ja foi publicada)."
exit 0
