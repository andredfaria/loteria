#!/bin/bash
# Faz backup dos volumes nomeados para arquivos tar.gz locais.
# Uso: bash scripts/volume-backup.sh
# Saída: backups/dados-YYYYMMDD.tar.gz  backups/saida-YYYYMMDD.tar.gz
set -e

BACKUP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/backups"
mkdir -p "$BACKUP_DIR"
DATE=$(date +%Y%m%d_%H%M%S)

echo "[backup] Exportando lotofacil_dados..."
docker run --rm \
  -v lotofacil_dados:/data \
  -v "$BACKUP_DIR":/out \
  alpine tar czf "/out/dados-$DATE.tar.gz" -C /data .
echo "[backup] → backups/dados-$DATE.tar.gz"

echo "[backup] Exportando lotofacil_saida..."
docker run --rm \
  -v lotofacil_saida:/data \
  -v "$BACKUP_DIR":/out \
  alpine tar czf "/out/saida-$DATE.tar.gz" -C /data .
echo "[backup] → backups/saida-$DATE.tar.gz"

echo "[backup] Concluído."
