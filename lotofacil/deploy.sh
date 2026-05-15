#!/bin/bash
# Script de deploy — volumes nomeados persistem entre atualizações.
# Uso: ./deploy.sh
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "[deploy] Atualizando código..."
git pull origin main

echo "[deploy] Rebuilding imagem..."
docker-compose build --no-cache

echo "[deploy] Subindo containers..."
docker-compose up -d

echo "[deploy] Status:"
docker-compose ps
echo ""

SORTEIOS=$(docker-compose exec -T dashboard sh -c 'ls /app/dados/concurso_*.json 2>/dev/null | wc -l' 2>/dev/null || echo "0")
MODELOS=$(docker-compose exec -T dashboard sh -c 'ls /app/saida/modelos/*.keras 2>/dev/null | wc -l' 2>/dev/null || echo "0")
echo "[deploy] Sorteios em volume: $SORTEIOS"
echo "[deploy] Modelos em volume:  $MODELOS"

if [ "$SORTEIOS" = "0" ]; then
  echo ""
  echo "[deploy] ⚠️  Volume de dados vazio. Use 'Atualizar Base' no dashboard para baixar o histórico."
  echo "[deploy]    Ou restaure um backup: bash scripts/volume-restore.sh"
fi
