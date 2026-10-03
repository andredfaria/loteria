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
  - GREEN, suíte padrão (`pytest`) de cada projeto: megasena 120, quina 210 e lotofacil 174 testes passando (504 no total).
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

## 2026-10-02 — Compose local na raiz, com portas presas em 127.0.0.1

**Decisão:** o `docker-compose.yml` da raiz é para uso local e publica as três portas só em `127.0.0.1` (`127.0.0.1:5001:5000`, `127.0.0.1:5002:5000` e `127.0.0.1:5003:5000`). Para expor um painel na rede, é preciso remover o prefixo `127.0.0.1:`, de preferência só com `DASHBOARD_PASSWORD` definida; o cabeçalho do compose explica isso.

**Motivo:** a versão inicial do compose (`"5001:5000"`) publicava em todas as interfaces. Com `DASHBOARD_PUBLICO=1`, que liga o painel sem senha, isso exporia o painel na rede local sem que ninguém tivesse decidido isso. Presas em `127.0.0.1`, só a própria máquina chega aos painéis, e quem quiser a rede faz isso de propósito.

**Evidência:** com o compose da raiz e a megasena (`docker compose up -d --wait`):

- `docker compose ps` mostra `127.0.0.1:5003->5000/tcp`; antes da mudança mostrava `0.0.0.0:5003->5000/tcp` e `[::]:5003->5000/tcp`.
- `ss -ltn` mostra um único listener na porta 5003, em `127.0.0.1`, e nenhum em `0.0.0.0`.
- Pelo loopback, `GET /healthz` responde 200 (`/api/status`, 401; `/`, 302). Pelo IP não-loopback da própria máquina, a conexão é recusada (`curl` sai com 7).
- `docker compose config` resolve `host_ip=127.0.0.1` nos três serviços.

## 2026-10-02 — CI `docker.yml` monta as imagens dos três painéis

**Decisão:** o workflow `.github/workflows/docker.yml` monta a imagem de cada painel (lotofacil, quina e megasena) com `docker build`, um job por projeto e com a pasta do projeto como contexto, igual ao EasyPanel. Roda em todo PR e em todo push na `main` que altere esses projetos ou o próprio workflow. Não publica nada.

**Motivo:** um build quebrado aparece no PR, antes de chegar ao EasyPanel. Antes, nenhum workflow montava as imagens, então um `Dockerfile` ou uma dependência quebrados só apareciam no deploy.

**Evidência:**

- Os builds locais de megasena (89 s) e quina (153 s), com o equivalente do comando do workflow (`docker build` com a pasta do projeto como contexto), terminaram com sucesso. A imagem da lotofacil, com TensorFlow, só é montada na CI.
- O filtro `paths`, em `push` e em `pull_request`, limita a execução a `lotofacil/**`, `quina/**`, `megasena/**` e ao próprio `docker.yml`: um PR que não mexe nesses projetos não paga o build.
- O workflow só constrói: `permissions: contents: read` e nenhum passo de login em registro ou de envio de imagem. O `actionlint` não aponta erro nele.
