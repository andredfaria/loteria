#!/bin/bash
set -e

mkdir -p /app/dados /app/saida

if ! ls /app/dados/concurso_*.json > /dev/null 2>&1; then
    echo "[entrypoint] Dados vazios. Use o botão 'Atualizar dados' no painel ou rode 'quina dados atualizar'."
fi

exec "$@"
