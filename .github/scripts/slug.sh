#!/usr/bin/env bash
# Slug para nome de branch a partir de um titulo: minusculas, sem acentos, so [a-z0-9-],
# no maximo 40 caracteres. Vazio vira "tarefa". Uso: slug.sh "Título da tarefa"
set -euo pipefail
python3 - "${1:-}" << 'PYEOF'
import re, sys, unicodedata
texto = unicodedata.normalize("NFKD", sys.argv[1]).encode("ascii", "ignore").decode("ascii").lower()
slug = re.sub(r"[^a-z0-9]+", "-", texto).strip("-")[:40].strip("-")
print(slug or "tarefa")
PYEOF
