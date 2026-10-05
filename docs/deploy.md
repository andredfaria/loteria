# Deploy dos painéis

Os projetos lotofacil, quina e megasena têm, cada um, um painel web publicado no EasyPanel como um app separado, a partir do `Dockerfile` da própria pasta. Os Dockerfiles usam a raiz do repositório como contexto para instalar o pacote compartilhado `nucleo/`.

## Configuração atual no EasyPanel

| App | Build Context | Dockerfile | Porta |
|-----|---------------|------------|-------|
| lotofacil | `/` | `lotofacil/Dockerfile` | `5000` |
| quina | `/` | `quina/Dockerfile` | `5000` |
| megasena | `/` | `megasena/Dockerfile` | `5000` |

O health check é o `HEALTHCHECK` do próprio `Dockerfile`: de 60 em 60 segundos (depois de 15 s de carência, e com limite de 5 s por tentativa), ele consulta `GET /healthz` dentro do container. A rota responde `200` com `{"status":"ok"}`, não pede login e não acessa banco nem dados. Se o seu painel de deploy pedir uma URL de health check, use `/healthz`: a `/api/status` exige login quando `DASHBOARD_PASSWORD` está definida e responderia `401`.

O workflow `docker.yml` monta as três imagens com contexto raiz em todo PR que mexe nos projetos, no núcleo ou na configuração do build.

> **Ação após a publicação desta fase:** em cada app no EasyPanel, defina Build Context como `/` (raiz do repositório) e Dockerfile como `lotofacil/Dockerfile`, `quina/Dockerfile` ou `megasena/Dockerfile`, conforme o app. Faça isso antes de disparar um novo deploy. Até atualizar os campos, o container publicado continua servindo, mas um novo build com a configuração antiga não encontrará `nucleo/`. O passo a passo, com os nomes exatos dos campos e como confirmar pelo log, está em [guias/easypanel.md](guias/easypanel.md).

## Volumes

Cada app precisa de volumes persistentes. Sem eles, os sorteios baixados, os modelos e os jogos gerados se perdem a cada redeploy. No EasyPanel o nome do volume é livre; o que importa é o caminho no container.

| Caminho no container | Apps | Conteúdo |
|----------------------|------|----------|
| `/app/dados` | os três | Sorteios baixados (JSON e SQLite). Na lotofacil, também os dados de lua e clima |
| `/app/saida` | os três | Modelos treinados. Na lotofacil, também jogos gerados, logs e o `treinos.db` |
| `/app/src/lotofacil/experimentos/saved_models` | só lotofacil | Modelos neurais (`.keras`) do pipeline experimental |

Na primeira execução o volume `dados` está vazio, e a imagem não semeia sorteios. Abra o painel e use **Atualizar dados** (quina e megasena) ou **Atualizar Base** (lotofacil) para baixar o histórico completo.

As imagens rodam como `appuser` (UID e GID 1000). Um volume nomeado novo herda o dono da pasta da imagem e já funciona; uma pasta do host montada à mão (bind mount) precisa permitir escrita ao UID 1000.

## Variáveis de ambiente

Defina em *Environment Variables* de cada app. Os painéis **falham fechado**: sem `DASHBOARD_PASSWORD` nem `DASHBOARD_PUBLICO=1` o painel não inicia. A justificativa está no [SECURITY.md](../SECURITY.md).

| Variável | Painéis | Obrigatória | Para que serve |
|----------|---------|-------------|----------------|
| `DASHBOARD_PASSWORD` | todos | uma das duas | Login por senha. Recomendada |
| `DASHBOARD_PUBLICO` | todos | uma das duas | `1` confirma o painel sem senha |
| `DASHBOARD_AUTH_SECRET` | todos | recomendada | Chave fixa da sessão de login |
| `DASHBOARD_MAX_JOBS` | só lotofacil | opcional | Teto de jobs pesados ao mesmo tempo (padrão `1`) |
| `OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS`, `MKL_NUM_THREADS`, `LOKY_MAX_CPU_COUNT`, `TF_NUM_INTRAOP_THREADS` | todos | opcional | Teto de threads de cálculo por processo (padrão `2`, definido no `Dockerfile`) |

O que cada uma faz e o que acontece se faltar:

- **`DASHBOARD_PASSWORD`**: exige login por senha em todas as rotas, menos `/healthz` e as páginas de login e logout. Sem ela **e** sem `DASHBOARD_PUBLICO=1`, o painel não inicia: o `gunicorn` reinicia o worker em loop, o log repete a mensagem que pede uma das duas variáveis e o container fica *unhealthy*. Uma variável vazia conta como ausente.
- **`DASHBOARD_PUBLICO`**: só vale o valor `1`. Confirma de propósito que o painel roda **sem senha**: quem alcançar a porta lê os dados e dispara trabalho. Use só atrás de rede ou túnel confiável. Se `DASHBOARD_PASSWORD` também estiver definida, o login continua exigido.
- **`DASHBOARD_AUTH_SECRET`**: chave fixa que assina a sessão de login. Sem ela, a chave é sorteada a cada início: todo restart ou redeploy derruba os logins (o log avisa), e com mais de um worker do gunicorn o login falha de forma intermitente (os `Dockerfile` usam 1 worker). Gere uma com `python3 -c "import secrets; print(secrets.token_hex(32))"`.
- **`DASHBOARD_MAX_JOBS`** (só lotofacil): teto de jobs pesados (geração, treino, backtest) ao mesmo tempo. Padrão `1`. Acima do teto, a API responde `429` em vez de enfileirar.
- **Threads de cálculo** (`OMP_NUM_THREADS` e afins): sem limite, `n_jobs=-1` do sklearn/LightGBM, o BLAS e o TensorFlow enxergam todos os núcleos do servidor, e um treino ocupa a máquina inteira, derrubando os outros apps. Os `Dockerfile` fixam `2`. Para um treino mais rápido num servidor folgado, sobrescreva todas com o mesmo valor (e `TF_NUM_INTEROP_THREADS`, padrão `1`). Para um teto rígido, defina também o limite de CPU do app no EasyPanel (*Advanced → Resources*).

## Subir localmente com o Docker Compose

O [`docker-compose.yml`](../docker-compose.yml) da raiz monta os três painéis com os mesmos `Dockerfile` do EasyPanel. Exige o Docker Compose 2.24 ou mais novo.

1. Crie, na raiz do repositório, um arquivo `.env` com as variáveis da seção anterior. O git o ignora; nunca o versione.

   Se você já tem um `.env`, edite-o em vez de rodar o comando abaixo: o `>` o **sobrescreve**.

   ```bash
   printf 'DASHBOARD_PASSWORD=%s\nDASHBOARD_AUTH_SECRET=%s\n' 'troque-esta-senha' "$(python3 -c 'import secrets; print(secrets.token_hex(32))')" > .env
   ```

   `troque-esta-senha` é só um exemplo; escolha uma senha sua e não use a do exemplo de verdade.

   Para um painel sem senha, escreva `DASHBOARD_PUBLICO=1` no lugar de `DASHBOARD_PASSWORD`. O compose só repassa ao container o que está no `.env`: variáveis exportadas no terminal não chegam lá. Se a senha tiver `$`, escreva o valor entre aspas simples (`DASHBOARD_PASSWORD='a$b'`); sem elas, o Compose lê `$b` como uma variável e corta a senha.

2. Suba o painel que quiser:

   ```bash
   docker compose up --build megasena     # ou quina, ou lotofacil
   ```

   Sem o nome, `docker compose up --build` sobe os três. A imagem da lotofacil inclui o TensorFlow (mais de 3 GB) e é, de longe, a maior das três. Para só montar a imagem de um painel, sem subir, use `make docker P=megasena`.

3. Abra o painel no navegador e entre com a senha:

   | Painel | Endereço |
   |--------|----------|
   | lotofacil | `http://127.0.0.1:5001` |
   | quina | `http://127.0.0.1:5002` |
   | megasena | `http://127.0.0.1:5003` |

O compose cria um volume nomeado para cada caminho da seção anterior (por exemplo `loteria_megasena_dados`; o prefixo é o nome da pasta do repositório). As portas ficam presas em `127.0.0.1`, então só esta máquina acessa os painéis. Para expor um painel na rede, remova o prefixo `127.0.0.1:` da porta no `docker-compose.yml`, de preferência só com `DASHBOARD_PASSWORD` definida.

Para parar:

```bash
docker compose down        # mantém os volumes (sorteios e modelos)
docker compose down -v     # apaga também os volumes
```

## Como verificar

```bash
curl -fsS http://localhost:5003/healthz    # megasena; use 5001 para a lotofacil e 5002 para a quina
docker compose ps                          # o STATUS passa a (healthy) depois de alguns segundos
```

A resposta esperada do `curl` é `{"status":"ok"}`.

## Problemas comuns

- **O build falha com `"/nucleo": not found` ou `"/lotofacil/entrypoint.sh": not found`.** O **Build Path** do app (aba *Source*) ainda aponta para a pasta do projeto. Mude para `/` e faça o deploy de novo. Ver [guias/easypanel.md](guias/easypanel.md).
- **O painel não abre e o container fica `unhealthy`.** Falta `DASHBOARD_PASSWORD` ou `DASHBOARD_PUBLICO=1` (ou o valor de `DASHBOARD_PUBLICO` não é exatamente `1`). O log (`docker compose logs megasena`) repete a mensagem que pede uma das duas. No compose, confira que o `.env` está na raiz do repositório.
- **O login cai a cada restart ou redeploy.** Falta `DASHBOARD_AUTH_SECRET`.
- **`Permission denied` ao gravar em `/app/dados` ou `/app/saida`.** O volume pertence a root, por exemplo porque foi criado por uma imagem antiga, que não tinha `USER`. Corrija o dono com `docker run --rm -v <volume>:/v alpine chown -R 1000:1000 /v`. O contexto está no [CHANGELOG](../CHANGELOG.md).
- **A API da lotofacil responde `429`.** Já há jobs pesados demais em andamento: espere um terminar ou aumente `DASHBOARD_MAX_JOBS`.
