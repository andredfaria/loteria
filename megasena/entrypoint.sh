#!/bin/bash
set -e

mkdir -p /app/dados /app/saida

if ! ls /app/dados/megasena_*.json > /dev/null 2>&1; then
    echo "[entrypoint] Dados vazios. Use o botão 'Atualizar dados' no painel ou rode 'megasena dados atualizar'."
fi

exec "$@"
