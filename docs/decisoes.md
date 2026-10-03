# Registro de decisões

Este arquivo registra o que saiu ou mudou na reorganização do monorepo, com data, motivo e evidência, para que ninguém precise reconstruir o porquê pelo histórico do git.

## 2026-10-02 — Rota `/healthz` e `HEALTHCHECK`

**Decisão:** os painéis de lotofacil, quina e megasena ganharam `GET /healthz`, que responde `200` com `{"status": "ok"}`, sem login e sem acessar banco ou dados. O `HEALTHCHECK` do `Dockerfile` de cada painel passou a consultar essa rota no lugar de `/api/status`.

**Motivo:** com `DASHBOARD_PASSWORD` definida, que é o modo normal de um deploy (os painéis falham fechado), `/api/status` exige sessão. O `HEALTHCHECK` não tem sessão, recebia 401 e o container ficava *unhealthy* com o painel funcionando. Uma rota própria de saúde, sem dados, resolve isso sem abrir nenhuma rota de negócio.

**Evidência:**

- A guarda `_check_auth` (um `before_request` em cada `server.py`) responde `401 {"error": "unauthorized"}` a todo `/api/*` sem sessão quando `DASHBOARD_PASSWORD` está definida. Era o que acontecia com `/api/status`, o alvo antigo do `HEALTHCHECK`.
- Testes novos, escritos antes da correção (RED) e passando depois (GREEN):
  - megasena e quina: 3 testes de rota na classe `TestGuardaDeRequisicao` (`/healthz` sem sessão responde 200; `/healthz` não abre o resto; `/healthz` não toca no banco) e 1 teste que confere o `HEALTHCHECK` do `Dockerfile`. No RED, 3 falharam e 1 passou: o teste de que o resto continua bloqueado, que é uma guarda e já passava antes da mudança.
  - lotofacil: 2 testes de rota e 1 do `Dockerfile`. No RED, os 3 falharam.
  - GREEN, suíte completa de cada projeto: megasena 120, quina 210 e lotofacil 174 testes passando (504 no total).
- Verificação em container real: as imagens de megasena e quina, montadas a partir dos `Dockerfile` do repositório e iniciadas com `DASHBOARD_PASSWORD` definida, chegaram a `healthy` com o próprio comando do `HEALTHCHECK` (só os intervalos foram encurtados, para não esperar). No mesmo container, sem sessão, `GET /healthz` respondeu 200, `GET /api/status` respondeu 401 e `GET /` respondeu 302 para `/login`. A imagem da lotofacil, com TensorFlow, não foi montada localmente; quem a monta é a CI (`.github/workflows/docker.yml`).

## 2026-10-02 — Remoção do `Dockerfile` legado da raiz

**Decisão:** o `Dockerfile` da raiz foi apagado. A imagem de cada painel vem só do `Dockerfile` da própria pasta (`lotofacil/`, `quina/` e `megasena/`), que é o que o EasyPanel usa e o que a CI monta.

**Motivo:** o arquivo já se declarava obsoleto e gerava uma imagem pior que a de produção. Mantê-lo convidava alguém a usá-lo por engano.

**Evidência:** o próprio arquivo, na última versão antes da remoção:

- O cabeçalho dizia "LEGADO — não use este Dockerfile".
- Usava `python:3.11-slim`; os `Dockerfile` atuais usam `python:3.12-slim`.
- Rodava `python -m lotofacil.interface.painel.server`, o servidor de desenvolvimento do Flask, e não o gunicorn dos `Dockerfile` atuais.
- Não criava usuário não-root; os atuais rodam como `appuser` (UID/GID 1000).
- Criava (`mkdir -p`) os caminhos `src/models_saved` e `src/lotofacil_lab/saved_models`, que não existem mais na árvore. Os modelos do lab ficam em `src/lotofacil/experimentos/saved_models`.

## 2026-10-02 — Remoção do `docker-compose.yml` legado da raiz

**Decisão:** o `docker-compose.yml` antigo da raiz foi apagado. O arquivo de mesmo nome que existe agora é o novo, com os três painéis (lotofacil na porta 5001, quina na 5002 e megasena na 5003), cada um construído a partir da própria pasta.

**Motivo:** o compose antigo montava um volume por cima do código do painel, então a imagem reconstruída não chegava ao container.

**Evidência:** o serviço `dashboard` montava o volume nomeado `lotofacil_db` em `/app/src`, que é onde fica o código do painel dentro da imagem. Um volume nomeado só recebe o conteúdo da imagem quando é criado vazio; depois disso, o que está no volume prevalece sobre o que a imagem traz naquele caminho. Por isso um rebuild continuava rodando o código velho guardado no volume.

## 2026-10-02 — Remoção do `.dockerignore` da raiz

**Decisão:** o `.dockerignore` da raiz foi apagado. O `lotofacil/.dockerignore` continua, porque o build do painel da lotofacil usa a pasta `lotofacil/` como contexto.

**Motivo:** ele só tinha efeito num build com contexto na raiz do repositório, e o único build assim era o do `Dockerfile` legado, que também saiu.

**Evidência:**

- O Docker lê o `.dockerignore` na raiz do contexto de build. Os builds atuais (EasyPanel, `docker-compose.yml` e CI) usam `lotofacil/`, `quina/` e `megasena/` como contexto, então o arquivo da raiz não era lido por nenhum deles.
- Mesmo para o build legado ele estava desatualizado: excluía `super-sete/`, `megasena/` e `dia-de-sorte/`, mas não `quina/`, e ainda listava dois caminhos que não existem mais: `lotofacil/src/models_saved/` e `lotofacil/src/lotofacil_lab/saved_models/`.

## 2026-10-02 — Remoção do compose e do `deploy.sh` da lotofacil

**Decisão:** `lotofacil/docker-compose.yml` e `lotofacil/deploy.sh` foram apagados.

**Motivo:** nenhum dos dois era o caminho de produção, e o uso local passou a ser coberto pelo compose novo da raiz.

**Evidência:** o deploy de produção é feito pelo EasyPanel, a partir do `Dockerfile` de cada painel, e o `docker-compose.yml` novo da raiz cobre o uso local dos três painéis. O `deploy.sh` só funcionava com o compose removido: fazia `git pull`, `docker-compose build --no-cache` e `docker-compose up -d`, e consultava o serviço `dashboard` desse compose com `docker-compose exec -T dashboard`.
