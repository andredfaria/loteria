#!/bin/bash
# Migra dados do bind mount local (/home/andre/lotofacil-dados) para o volume nomeado.
# Execute uma vez após trocar para named volumes.
# Uso: bash scripts/volume-migrate-local.sh
set -e

LOCAL_DADOS="/home/andre/lotofacil-dados"

if [ ! -d "$LOCAL_DADOS" ]; then
  echo "[migrate] Diretório local não encontrado: $LOCAL_DADOS"
  echo "[migrate] Nada a migrar. Use 'Atualizar Base' no dashboard."
  exit 0
fi

COUNT=$(ls "$LOCAL_DADOS"/concurso_*.json 2>/dev/null | wc -l)
echo "[migrate] Encontrados $COUNT sorteios em $LOCAL_DADOS"

echo "[migrate] Copiando para volume lotofacil_dados..."
docker run --rm \
  -v lotofacil_dados:/dest \
  -v "$LOCAL_DADOS":/src:ro \
  alpine sh -c "cp -r /src/. /dest/"

DEST_COUNT=$(docker run --rm -v lotofacil_dados:/data alpine sh -c 'ls /data/concurso_*.json 2>/dev/null | wc -l')
echo "[migrate] ✅ $DEST_COUNT arquivos no volume"
