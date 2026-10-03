# Changelog

Este projeto segue o [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e ainda não tem versões publicadas.

## [Não publicado]

### Adicionado

- Rota `GET /healthz` nos painéis de lotofacil, quina e megasena. Responde `200` com `{"status": "ok"}`, sem login e sem acessar banco ou dados.
- Novo `docker-compose.yml` na raiz, que substitui o legado e sobe os três painéis: lotofacil na porta 5001, quina na 5002 e megasena na 5003.
- Workflow de CI `docker.yml`, que monta as imagens dos três painéis em todo PR e em todo push na `main` que alterem esses projetos. Não publica nada.

### Alterado

- Quem usava localmente o `lotofacil/docker-compose.yml` não reaproveita os volumes: o projeto Compose agora é o da raiz do repositório e o volume dos modelos neurais passou de `lotofacil_lab_models` para `lotofacil_modelos_lab`. Os volumes do EasyPanel não mudam.

### Corrigido

- Container dos painéis (lotofacil, quina e megasena) ficava *unhealthy* com `DASHBOARD_PASSWORD` definida, porque o `HEALTHCHECK` consultava `/api/status`, que exige login. Agora consulta `/healthz`.

### Removido

- `Dockerfile`, `docker-compose.yml` e `.dockerignore` legados da raiz. Motivos em [docs/decisoes.md](docs/decisoes.md).
- `lotofacil/docker-compose.yml` e `lotofacil/deploy.sh`. Motivos em [docs/decisoes.md](docs/decisoes.md).

### Segurança

- `.env` agora é ignorado pelo git na raiz, para que a senha do painel não seja versionada por engano.
- O `docker-compose.yml` publica as portas só em `127.0.0.1`. Para expor os painéis na rede, é preciso remover esse prefixo, de preferência só com `DASHBOARD_PASSWORD` definida.
