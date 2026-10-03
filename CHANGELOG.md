# Changelog

Este projeto segue o [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e ainda não tem versões publicadas.

## [Não publicado]

### Adicionado

- Rota `GET /healthz` nos painéis de lotofacil, quina e megasena. Responde `200` com `{"status": "ok"}`, sem login e sem acessar banco ou dados.
- Novo `docker-compose.yml` na raiz, que substitui o legado e sobe os três painéis: lotofacil na porta 5001, quina na 5002 e megasena na 5003.
- Workflow de CI `docker.yml`, que monta as imagens dos três painéis em todo PR e em todo push na `main` que alterem esses projetos. Não publica nada.

### Corrigido

- Container dos painéis (lotofacil, quina e megasena) ficava *unhealthy* com `DASHBOARD_PASSWORD` definida, porque o `HEALTHCHECK` consultava `/api/status`, que exige login. Agora consulta `/healthz`.

### Removido

- `Dockerfile`, `docker-compose.yml` e `.dockerignore` legados da raiz. Motivos em [docs/decisoes.md](docs/decisoes.md).
- `lotofacil/docker-compose.yml` e `lotofacil/deploy.sh`. Motivos em [docs/decisoes.md](docs/decisoes.md).
