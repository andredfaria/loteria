#!/bin/bash
# Script de deploy para VPS — preserva dados entre atualizações.
# Uso: ./deploy.sh
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "[deploy] Atualizando código..."
git pull origin main

echo "[deploy] Rebuilding imagem..."
docker-compose build --no-cache

echo "[deploy] Subindo containers (sem down -v para preservar dados)..."
docker-compose up -d

echo "[deploy] Status:"
docker-compose ps
echo ""
echo "[deploy] Dados em ./dados/: $(ls ./dados/concurso_*.json 2>/dev/null | wc -l) sorteios"
echo "[deploy] Modelos em ./saida/modelos/: $(ls ./saida/modelos/*.keras 2>/dev/null | wc -l) arquivos"
