# Registro de decisões

Este arquivo registra o que saiu ou mudou na reorganização do monorepo, com data, motivo e evidência, para que ninguém precise reconstruir o porquê pelo histórico do git.

A reorganização acontece em fases numeradas: 1 (saúde dos painéis e raiz Docker), 2 (higiene e open source), 3 (núcleo, megasena e troca do contexto de build), 4 (ML no núcleo e quina), 5 (dia-de-sorte e super-sete) e 6 (lotofacil). As entradas abaixo cobrem as fases 1 e 2; quando uma entrada cita a fase 3 ou a 6, é trabalho que ainda vai ser feito.

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

**Motivo:** um build quebrado aparece no PR, antes de chegar ao EasyPanel. Antes, nenhum workflow montava as imagens, então um `Dockerfile` quebrado só aparecia no deploy.

**Evidência:**

- Os builds locais de megasena (89 s) e quina (153 s), com o equivalente do comando do workflow (`docker build` com a pasta do projeto como contexto), terminaram com sucesso. A imagem da lotofacil, com TensorFlow, só é montada na CI.
- O filtro `paths`, em `push` e em `pull_request`, limita a execução a `lotofacil/**`, `quina/**`, `megasena/**` e ao próprio `docker.yml`: um PR que não mexe nesses projetos não paga o build.
- O workflow só constrói: `permissions: contents: read` e nenhum passo de login em registro ou de envio de imagem. O `actionlint` não aponta erro nele.

## 2026-10-03 — `.gitignore` enxuto: regra de projeto no projeto, caminhos mortos fora

**Decisão:** o `.gitignore` da raiz guarda só o que vale para o repositório inteiro: venvs, caches do Python, modelos `.joblib`, `.keras`, `.h5` e `.pkl`, bancos SQLite, `.env`, ferramentas de IA e arquivos de IDE. Nos projetos quina, megasena, dia-de-sorte e super-sete, o `.gitignore` da própria pasta ignora `/dados` e `/saida`; o da lotofacil ignora também `/backups`, `portfolio_*.txt` e `portfolio_*.json`. Saíram as regras de caminhos da lotofacil que não existem mais.

**Motivo:** o arquivo da raiz misturava regra global com caminhos de um projeto só, muitos de uma estrutura que já não existe. Cada regra morta é ruído que esconde as que valem e pode esconder um arquivo versionado por engano.

**Evidência:**

- O `.gitignore` da raiz passou de 96 para 57 linhas (de 72 para 42 regras), e o da lotofacil, de 58 para 15 linhas.
- Caminhos mortos que saíram (nenhum existe hoje, nem no disco nem no git):
  - `lotofacil/data/…`, `lotofacil/src/models_saved/`, `lotofacil/app/models_saved/`, `lotofacil/portfolio/backtest_validacao.json` e `lotofacil/legado/`: nunca foram rastreados, e nenhum commit do histórico toca esses caminhos.
  - `lotofacil/ml/…`, `lotofacil/output/…`, `lotofacil/src/lotofacil_ml/relatorio.txt` e `src/lotofacil_lab/saved_models/` (esta, do `lotofacil/.gitignore`): as pastas saíram no commit `17172c6` (2026-05-13, "consolidação estrutural completa em 8 ondas"). Os modelos do lab ficam hoje em `src/lotofacil/experimentos/saved_models`.
- Regras que migraram, não sumiram: `lotofacil/dados` e as `dados/*.json` de lotofacil, super-sete e dia-de-sorte viraram `/dados` em cada projeto; `lotofacil/saida/` virou `/saida`; `backups/` virou `/backups`. As duplicatas da raiz (`.cursor/`, `.vscode/`, `.idea/`, `.DS_Store`, `Thumbs.db`, `.worktrees/` e `venv/`) e as regras `*.pyo`, `*.pyd`, `src/lotofacil.db` e `prompt-*.md` já eram cobertas por outras (`*.py[cod]`, `*.db`, `prompt*.md` e as da própria raiz).
- `git ls-files -ci --exclude-standard` (arquivos rastreados e ignorados) devolve 0 linhas: nenhuma regra nova esconde um arquivo versionado. Os 9 `*.meta.json` de `lotofacil/src/lotofacil/experimentos/saved_models/` seguem versionados de propósito e fora das regras (`git check-ignore` devolve 1 para todos).
- `.env.*` com `!.env.example`: `.env.local`, `.env.production`, `quina/.env.local` e `lotofacil/.env.staging` são ignorados; `.env.example`, na raiz e em `quina/`, `megasena/` e `lotofacil/`, não é (`git check-ignore -q` devolve 1; a regra decisiva é a negação). `.eggs/` entrou na seção Python. `ruvector.db` saiu da lista porque `*.db` já o cobre.
- `/src/lotofacil/experimentos/output/` é ignorado porque `lotofacil lab ablation` e `lab compare` gravam ali `metrics.json`, `report.md` e dois PNG por execução.
- `/dados` fica sem barra final de propósito, no `lotofacil/.gitignore` e no `quina/.gitignore`: `dados` costuma ser um symlink para fora do repositório (`lotofacil/dados` e `quina/dados` são), e uma regra com `/` no fim só casa diretório. O `git status --ignored` lista os dois symlinks sem barra e os diretórios com barra.
- Exceção temporária: `/src/lotofacil/saida/`. O comando `lotofacil portfolio` grava os `portfolio_N.json` em `lotofacil/src/lotofacil/saida/jogos/`, e não em `lotofacil/saida/jogos/`: em `interface/cli/portfolio.py:351` a conta do caminho usa 3 `.parent` em vez de 5 (o `_DADOS_DIR`, na linha 306 do mesmo arquivo, usa 5). A regra antiga `saida/` (em qualquer nível) cobria isso; a `/saida` nova, não. A regra sai junto com o erro de caminho, quando ele for corrigido (fase 6).

## 2026-10-03 — Artefatos de IA fora do git

**Decisão:** `**/docs/superpowers/` e `**/.superpowers/` são ignorados em qualquer nível, e os 39 arquivos que já estavam versionados saíram do índice: `lotofacil/docs/superpowers/` (27), `quina/docs/superpowers/` (6) e `lotofacil/.superpowers/` (6). Continuam no disco de quem os gerou e no histórico do git.

**Motivo:** são planos, specs e rascunhos de ferramentas de IA, de uso local de desenvolvimento, e não fazem parte do projeto. A regra antiga `docs/superpowers/` tinha barra no meio e só valia na raiz, então os dois `docs/superpowers/` de projeto entraram no git sem ninguém notar.

**Evidência:**

- Antes da mudança, `git ls-files` contava 6 + 27 + 6 = 39 arquivos nesses três diretórios, e `git ls-files -ci --exclude-standard` listava só os 6 de `lotofacil/.superpowers/`: os outros 33 nem constavam como ignorados. O commit `09373fb` tirou os 39 do índice.
- Depois do `git rm -r --cached`: 0 rastreados nos três diretórios e 39 de 39 ignorados (`git check-ignore`). Os arquivos seguem no disco, com o mesmo sha256 de antes.
- Sair do índice não apaga o histórico: os arquivos continuam nos commits antigos (o último que os tocou antes da remoção é de 2026-07-09). Limpar o histórico seria outra decisão, com reescrita e republicação.

## 2026-10-03 — `ruff.toml` sem `exclude` nem `extend-exclude`

**Decisão:** o `ruff.toml` não define `exclude` nem `extend-exclude`. Um comentário no arquivo explica por quê e avisa para não usar `exclude`.

**Motivo:** o `exclude` antigo substituía os padrões do ruff e, com isso, perdia `dist`, `.git`, `.eggs`, `node_modules` e `site-packages`. Também listava `**/__pycache__` (só guarda `.pyc`, que o ruff não lê) e `*/legado` (pasta que não existe mais). Um `extend-exclude = ["*/venv", "*/.venv"]`, que o trocou numa primeira versão, era redundante: os padrões do ruff já casam `venv` e `.venv` por nome, em qualquer nível.

**Evidência:** ruff 0.16.5.

- `ruff check . --show-files` listava os mesmos 375 arquivos com e sem o bloco, nenhum em `venv`; sem respeitar o `.gitignore` (`--no-respect-gitignore`) eram 376 nos dois casos, também nenhum em `venv`. `ruff check .` segue com `All checks passed!`.
- Num experimento fora do repositório, com `--isolated` (só os padrões de fábrica), o ruff pulou `venv`, `.venv`, `dist`, `site-packages`, `node_modules`, `_build` e `.eggs` em qualquer nível e **não** pulou `build/`. No repositório, `build/` fica de fora porque o ruff respeita o `.gitignore`.

## 2026-10-03 — Remoção das amostras `dados/sample/` da super-sete e da dia-de-sorte

**Decisão:** `super-sete/dados/sample/` (100 arquivos) e `dia-de-sorte/dados/sample/` (15) foram apagados do repositório (commit `5fc54a2`). Os testes usam `testes/fixtures/sample_draws/`.

**Motivo:** nada lê essas pastas, elas não cumpriam o que prometiam (os 100 sorteios mais recentes) e já eram ignoradas pelo `.gitignore` de cada projeto.

**Evidência:**

- Busca por `sample` em `src/` e `testes/` dos dois projetos: nenhuma referência a `dados/sample` (só `random.sample`, `min_samples_leaf` e `testes/fixtures/sample_draws`).
- super-sete: concursos 8 a 798, não contíguos (o dataset completo, baixado pela CLI, ia até o 872); só 26 dos 100 estavam entre os 100 mais recentes. dia-de-sorte: concursos 1183 a 1197 (o completo ia até o 1244).
- Antes da remoção, os 115 arquivos eram "rastreados e ignorados": o `/dados` do `.gitignore` do projeto já os escondia. Eram idênticos, byte a byte, aos de mesmo nome em `dados/`, e continuam no histórico do git.

## 2026-10-03 — Documentos reorganizados: `pesquisa/` e nomes só em ASCII

**Decisão:** os documentos de pesquisa de cada projeto foram para `<projeto>/docs/pesquisa/`, e todos os documentos passaram a ter nome só em ASCII, em minúsculas e com hífens. Foram 18 renomeações com `git mv` (commit `7659e7f`):

- `docs/guia_e_racional_de_avalia_o_de_bol_es.md` virou `docs/guias/avaliacao-de-boloes.md`.
- Na lotofacil, `DASHBOARD-OVERVIEW.md` virou `painel.md`, `dicionario_dados_ml.md` virou `dicionario-dados-ml.md`, `clima/README.md` virou `clima.md` e `strategies/11-numbers.md` virou `estrategias/onze-dezenas.md`. Os três relatórios de pesquisa foram para `pesquisa/`: `hierarquia-de-estrategias.md`, `estrategias-racionais.md` e `validacao-ml-3500-3580.md` (antes, nomes como "Relatório Técnico_ Estratégias Racionais para a Lotofácil.md").
- Na super-sete, o relatório de análise virou `docs/pesquisa/relatorio-de-analise.md`.
- Na dia-de-sorte, os nove documentos de estratégia, de `docs/01_equilibrio_par_impar.md` a `docs/09_mes_da_sorte.md`, viraram `docs/pesquisa/01-equilibrio-par-impar.md` a `docs/pesquisa/09-mes-da-sorte.md`.

**Motivo:** `:` não é aceito em nome de arquivo no Windows, o que impede o checkout; acento e espaço quebram links e variam entre sistemas de arquivos. Separar `pesquisa/` do resto também distingue os estudos e relatórios dos documentos que descrevem o próprio sistema (`painel.md` e `dicionario-dados-ml.md`, por exemplo).

**Evidência:**

- Antes da mudança, `git ls-files` listava 4 arquivos com acento, espaço ou `:` no nome: 3 foram renomeados e 1 foi apagado (o arquivo vazio da dia-de-sorte, na entrada seguinte). Depois, nenhum.
- As 18 renomeações saíram com 100% de similaridade (`R100` no `git diff -M`): o conteúdo ficou intacto, e `git log --follow` acompanha o histórico de cada arquivo.
- As referências foram atualizadas em 8 arquivos (commit `508ee03`): `megasena/README.md`, `lotofacil/README.md`, `dia-de-sorte/README.md`, uma docstring em `megasena/src/megasena/servicos/bolao.py` e outra em `megasena/testes/unidade/test_bolao.py`, um comentário em `lotofacil/src/lotofacil/experimentos/config.py` e uma docstring em `.../features/strategy_priors.py`. O `lotofacil/scripts/build_ml_dataset.py` é a única mudança de código de verdade: ele grava o dicionário de dados, e sem trocar o nome do arquivo no literal a próxima execução recriaria `dicionario_dados_ml.md` ao lado do renomeado.

## 2026-10-03 — Remoção de documentos obsoletos de lotofacil e dia-de-sorte

**Decisão:** foram apagados sete arquivos: `lotofacil/PRD.md`, `lotofacil/docs/PRD-dashboard.md`, `lotofacil/docs/architecture.md`, `lotofacil/docs/development.md`, `dia-de-sorte/docs/api-doc.md`, `dia-de-sorte/docs/2026-04-07-analisador-diadesorte.md` e `dia-de-sorte/docs/analise-estatística-completa-estratégia-de-bolao.md` (commit `7659e7f`).

**Motivo:** descreviam um sistema que não existe mais, eram PRDs já implementados, copiavam documentação de terceiros ou estavam vazios. Documento que descreve o que não existe engana quem chega ao repositório. Todos continuam no histórico do git.

**Evidência:**

- `architecture.md` e `development.md` citam `src/main.py`, `src/strategies/`, `src/features/`, `src/models/` e `data/`; nenhum existe em `lotofacil/`. A CLI de hoje é `lotofacil` (`lotofacil.interface.cli.app:app`), com os grupos `dados`, `modelo`, `prever`, `portfolio`, `lab` e `campeao`, e os testes ficam em `testes/`.
- Os dois PRDs são de maio e cobrem o que já está implementado (CLI `dados`, `modelo`, `lab` e `portfolio`, e o painel Flask). O `PRD-dashboard.md` cita `GET /api/stream/:task_id`, que não existe em `server.py` (hoje há `/api/jobs/<task_id>/poll` e `/api/jobs/<task_id>/stream`); a lista atual de rotas está no `lotofacil/README.md`.
- `api-doc.md` é cópia da documentação da API de terceiros `loteriascaixa-api.herokuapp.com` (URL base, 3 endpoints e exemplos genéricos com dados da Mega-Sena). O que os projetos precisam dela está em `docs/api-externa.md`, e o `dia-de-sorte/README.md` linka o projeto da API.
- `2026-04-07-analisador-diadesorte.md` é um plano de implementação, feito para agentes de IA, do `analisar_diadesorte.py`, que já existe. Ele cita `tests/test_analise.py` em 22 linhas, e `dia-de-sorte/tests/` não existe (os testes estão em `testes/`).
- `analise-estatística-completa-estratégia-de-bolao.md` tinha 0 bytes, desde o commit inicial.

## 2026-10-03 — `lotofacil/docs/curl.md` vira `docs/api-externa.md`

**Decisão:** o `lotofacil/docs/curl.md` foi movido para `docs/api-externa.md`, na raiz, com o título "API externa de resultados (loteriascaixa-api)" e uma nota no topo: o exemplo é da Lotofácil, as outras loterias trocam o slug na URL, e o espelho no Heroku é um serviço de terceiros, não oficial da Caixa. O resto do conteúdo é o do arquivo original. Os READMEs de `lotofacil` e `dia-de-sorte` linkam o documento.

**Motivo:** o documento descreve a API que os projetos usam para baixar os sorteios, e não rotas de um projeto. Na pasta da lotofacil, ele parecia coisa só dela. A primeira versão desta reorganização o apagava, por ter tomado as rotas da API externa por rotas do painel que não existem; a decisão foi revertida na mesma fase.

**Evidência:** `API_BASE_URL = "https://loteriascaixa-api.herokuapp.com/api"` está no `infra/config.py` dos cinco projetos, e a lotofacil ainda chama `.../api/lotofacil` em `interface/cli/dados.py` e `interface/cli/portfolio.py`. O arquivo restaurado era idêntico ao antigo (mesmo hash de blob) antes de receber o título novo e a nota (commit `009e12b`).

## 2026-10-03 — Nomes de arquivo portáveis e links relativos verificados na CI

**Decisão:** o `lint.yml` ganhou dois passos. O primeiro falha se algum arquivo versionado tiver acento, espaço ou `:` no nome. O segundo, `.github/scripts/verificar_links.py`, falha se um link relativo de um `.md` versionado apontar para um arquivo que não existe; ele ignora links com esquema (`http`, `mailto`...), âncoras puras, blocos de código e código inline.

**Motivo:** o problema que as duas checagens pegam é silencioso: um nome com `:` só aparece quando alguém tenta clonar no Windows, e um link quebrado só quando alguém clica nele. Num repositório aberto, quem clonar precisa conseguir abrir e navegar a documentação.

**Evidência:**

- O verificador passou limpo no estado anterior à reorganização e acusou exatamente 1 link quebrado depois de mover os documentos (`megasena/README.md`, que apontava para `docs/guia_e_racional_de_avalia_o_de_bol_es.md`), corrigido em seguida (commit `508ee03`). Rodado num clone limpo do HEAD, os dois passos saem com 0.
- O passo de nomes falha fechado: só a saída 1 do `grep` (nada encontrado) conta como sucesso, e uma falha do `git` ou do `grep` derruba o passo. A primeira versão (commit `9875387`) tinha um `|| true` que as escondia; o commit `8531148` corrigiu isso. Testado com `git` e `grep` simulados falhando, e num repositório descartável com nomes ruins.
- O verificador não cobre links por referência, `<a href>` e `<img src>`, âncoras de arquivo (só o arquivo é checado), alvo entre `<...>` nem alvo com parênteses; a docstring do script lista os limites (commit `6df3e3f`).

## 2026-10-03 — Arquivos de comunidade e `Makefile`

**Decisão:** o repositório ganhou `CODE_OF_CONDUCT.md`, templates de issue (bug e melhoria) e de pull request, `.github/dependabot.yml`, `.editorconfig` e um `Makefile` na raiz com os alvos `ajuda`, `instalar`, `testar`, `lint` e `docker` (commits `f778ae8`, `79258bc` e `f914a84`).

**Motivo:** o repositório é aberto, e quem chega precisa saber como se comportar, como reportar um problema, como abrir um PR e como rodar o projeto sem ler cinco READMEs. O `Makefile` dá o mesmo comando para os cinco projetos, cada um com o próprio venv.

**Evidência:**

- O código de conduta é uma adaptação em português do Contributor Covenant 2.1. Não publica e-mail: aponta para o canal privado que o `SECURITY.md` já descreve (um *security advisory* privado no GitHub).
- O Dependabot cobre `pip`, nas pastas dos cinco projetos, e `github-actions`, na raiz, com verificação semanal. Como o `pyproject.toml` de cada projeto usa faixas `>=`, quase não haverá PR de versão para pip; a varredura de vulnerabilidades é a do `pip-audit` (`seguranca.yml`, também semanal).
- `.editorconfig`: UTF-8, LF e 4 espaços (2 em YAML, JSON, HTML, CSS e JS), tabs no `Makefile`, e `*.md` sem remover espaço no fim da linha.
- `Makefile`: `make testar` sem `P` roda os cinco projetos; `P` é validado contra a lista (`P=inexistente`, `P=mega` e `P=quina/` saem com código 2 e listam as opções); `make docker` só aceita os três projetos com `Dockerfile`; `make lint` avisa como instalar o `ruff` quando ele falta. `make testar P=megasena` roda a suíte (120 testes passando) e `make lint` passa com `All checks passed!`.

## 2026-10-03 — `.dockerignore` novo da raiz fica para a fase 3

**Decisão:** o `.dockerignore` **novo** da raiz, que a fase 1 previa, não foi criado. (O legado da raiz foi apagado na fase 1; ver a entrada "Remoção do `.dockerignore` da raiz".) O novo nasce na fase 3, quando o build dos painéis passar a usar a raiz do repositório como contexto, e precisará excluir `.env` e `**/.env`.

**Motivo:** o Docker só lê o `.dockerignore` que está na raiz do contexto de build, e hoje nenhum build usa a raiz como contexto. Quando usar, sem essa exclusão um `COPY` poderia levar para dentro da imagem um `.env` com a senha do painel.

**Evidência:** os três builds que existem usam a pasta do projeto como contexto: o EasyPanel (Build Context `lotofacil`, `quina` ou `megasena`), o `docker-compose.yml` (`build: ./lotofacil` e equivalentes) e o `docker.yml` (`docker build ... "${{ matrix.projeto }}"`). O único `.dockerignore` que existe e que esses builds leem é o `lotofacil/.dockerignore`.

## 2026-10-03 — `.env.example` ainda não existe

**Decisão:** o repositório não tem `.env.example`. No lugar dele, o [deploy.md](deploy.md) traz a tabela das variáveis dos painéis, e o cabeçalho do `docker-compose.yml` manda copiar o `.env.example` para `.env` (se existir) ou criar um `.env` com as variáveis do `deploy.md`.

**Motivo:** o arquivo está planejado desde a fase 1, e o `.gitignore` já o libera (`!.env.example`). Mas a ferramenta usada na reorganização não pode ler nem criar arquivos `.env*`: é uma regra de permissão do dono do repositório, e o bloqueio não foi contornado.

**Evidência:** a criação do arquivo foi negada por essa regra, nas fases 1 e 2. Pendente: o dono cria o arquivo, com as variáveis da tabela do `deploy.md`, ou estreita a regra. Quando o arquivo existir, o cabeçalho do compose pode perder o "se existir" e o CHANGELOG ganha a linha dele.
