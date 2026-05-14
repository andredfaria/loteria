#!/bin/bash
set -e

# Popula /app/dados/ com os sorteios de exemplo se o volume estiver vazio.
# Isso garante que o dashboard funcione logo no primeiro boot sem precisar
# rodar "dados atualizar" manualmente. Use o dashboard para buscar o histórico
# completo depois.
if ! ls /app/dados/concurso_*.json > /dev/null 2>&1; then
    echo "[entrypoint] Volume de dados vazio — copiando dados de exemplo..."
    cp /app/dados_seed/concurso_*.json /app/dados/ 2>/dev/null || true
    COUNT=$(ls /app/dados/concurso_*.json 2>/dev/null | wc -l)
    echo "[entrypoint] $COUNT sorteios carregados do seed. Use o dashboard para buscar o histórico completo."
fi

exec "$@"
