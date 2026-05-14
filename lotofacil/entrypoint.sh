#!/bin/bash
set -e

# Garante estrutura de diretórios no volume montado.
# Não semeia concursos — assim local_max=0 e "Atualizar Base" busca do concurso 1
# até o mais recente automaticamente na primeira execução.
mkdir -p /app/dados/lua /app/dados/clima /app/saida/jogos /app/saida/modelos /app/saida/logs

if ! ls /app/dados/concurso_*.json > /dev/null 2>&1; then
    echo "[entrypoint] Dados vazios. Use 'Atualizar Base' no dashboard para baixar o histórico completo (concurso 1 → atual)."
fi

exec "$@"
