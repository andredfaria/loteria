#!/bin/bash
# Restaura volumes a partir dos backups mais recentes em backups/.
# Uso: bash scripts/volume-restore.sh
# Opcionalmente: bash scripts/volume-restore.sh backups/dados-20240101.tar.gz backups/saida-20240101.tar.gz
set -e

BACKUP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/backups"

DADOS_FILE="${1:-$(ls -t "$BACKUP_DIR"/dados-*.tar.gz 2>/dev/null | head -1)}"
SAIDA_FILE="${2:-$(ls -t "$BACKUP_DIR"/saida-*.tar.gz 2>/dev/null | head -1)}"

if [ -z "$DADOS_FILE" ] || [ ! -f "$DADOS_FILE" ]; then
  echo "[restore] ❌ Nenhum backup de dados encontrado em $BACKUP_DIR"
  exit 1
fi

echo "[restore] Restaurando lotofacil_dados de $DADOS_FILE..."
docker run --rm \
  -v lotofacil_dados:/data \
  -v "$BACKUP_DIR":/out \
  alpine sh -c "cd /data && tar xzf /out/$(basename "$DADOS_FILE")"
echo "[restore] ✅ dados restaurados"

if [ -n "$SAIDA_FILE" ] && [ -f "$SAIDA_FILE" ]; then
  echo "[restore] Restaurando lotofacil_saida de $SAIDA_FILE..."
  docker run --rm \
    -v lotofacil_saida:/data \
    -v "$BACKUP_DIR":/out \
    alpine sh -c "cd /data && tar xzf /out/$(basename "$SAIDA_FILE")"
  echo "[restore] ✅ saida restaurado"
fi

echo "[restore] Concluído."
