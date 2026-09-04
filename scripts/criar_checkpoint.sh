#!/bin/zsh

set -euo pipefail

RAIZ_PROJETO="$(cd -- "$(dirname -- "$0")/.." && pwd)"
ETAPA="${1:-manual}"
ETAPA_SEGURA="${ETAPA//[^A-Za-z0-9_-]/_}"
MOMENTO="$(date +%Y-%m-%d_%H-%M-%S)"
PASTA_BACKUPS="$RAIZ_PROJETO/backups"
ARQUIVO="$PASTA_BACKUPS/BFT_WIN_3_2_${ETAPA_SEGURA}_${MOMENTO}.tar.gz"
MANIFESTO="$PASTA_BACKUPS/BFT_WIN_3_2_${ETAPA_SEGURA}_${MOMENTO}.md"

mkdir -p "$PASTA_BACKUPS"
cd "$RAIZ_PROJETO"

tar -czf "$ARQUIVO" \
    --exclude='*/__pycache__' \
    --exclude='*.pyc' \
    --exclude='pc/BFT WIN 3.1.app' \
    --exclude='pc/BFT WIN 3.2.app' \
    pc web mobile core tests assets scripts requirements.txt LEIA-ME.md \
    VERSAO_ATUAL.md MAPA_DO_PROJETO.md CHECKLIST_DO_PROJETO.md

{
    print -r -- "# Checkpoint BFT WIN 3.2"
    print
    print -r -- "- Etapa: $ETAPA"
    print -r -- "- Criado em: $(date '+%Y-%m-%d %H:%M:%S')"
    print -r -- "- Arquivo: $(basename "$ARQUIVO")"
    print -r -- "- SHA-256: $(shasum -a 256 "$ARQUIVO" | awk '{print $1}')"
    print -r -- "- Conteudo: fontes, testes, assets, scripts e documentacao."
    print -r -- "- Excluido: aplicativo compilado e caches; o app e recriavel a partir das fontes."
} > "$MANIFESTO"

print "Checkpoint criado: $ARQUIVO"
