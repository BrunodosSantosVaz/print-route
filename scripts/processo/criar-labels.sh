#!/usr/bin/env bash
# Cria (ou atualiza) as labels padrao do processo em um repositorio.
# Uso: scripts/criar-labels.sh OWNER/REPO
set -euo pipefail

REPO="${1:?Uso: $0 OWNER/REPO}"

# nome|cor|descricao
LABELS=(
  "epic|5319E7|Epico: ideia/iniciativa grande, quebrada em tarefas"
  "task|1D76DB|Tarefa: unidade de trabalho de um epico (inclui testes)"
  "bug|D73A4A|Algo nao funciona como deveria"
  "hotfix|B60205|Correcao urgente em producao"
  "testing|6F42C1|Testes e evidencias"
  "documentation|0075CA|Documentacao"
  "prioridade:alta|B60205|Prioridade alta"
  "prioridade:media|FBCA04|Prioridade media"
  "prioridade:baixa|C2E0C6|Prioridade baixa"
  "severidade:critico|B60205|Sistema fora, perda de dados ou seguranca"
  "severidade:alto|D93F0B|Funcao principal quebrada sem alternativa"
  "severidade:medio|FBCA04|Falha com contorno"
  "severidade:baixo|C2E0C6|Cosmetico ou raro"
  "aprovado|0E8A16|PR aprovado pelo dono: entra na proxima integracao da release"
  "sem-executavel|BFD4F2|Nao altera o executavel (docs, testes, CI): dispensa homologacao e release"
  "enhancement|A2EEEF|Melhoria de funcionalidade existente"
  "dependencies|0366D6|Atualizacao de dependencias"
  "ignore-for-release|EDEDED|Fora das notas de release"
  "good first issue|7057FF|Bom para quem esta comecando"
  "help wanted|008672|Ajuda bem-vinda"
)

for entry in "${LABELS[@]}"; do
  IFS='|' read -r name color description <<<"$entry"
  gh label create "$name" --repo "$REPO" --color "$color" \
    --description "$description" --force >/dev/null
  echo "label ok: $name"
done
