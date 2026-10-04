# Deploy dos painéis

Os projetos lotofacil, quina e megasena têm, cada um, um painel web publicado no EasyPanel como um app separado, a partir do `Dockerfile` da própria pasta. Este documento traz a configuração atual de cada app, os volumes, as variáveis de ambiente, como subir os painéis localmente com o Docker Compose e como conferir que estão de pé.

## Configuração atual no EasyPanel

| App | Build Context | Dockerfile | Porta |
|-----|---------------|------------|-------|
| lotofacil | `lotofacil` | `Dockerfile` | `5000` |
| quina | `quina` | `Dockerfile` | `5000` |
| megasena | `megasena` | `Dockerfile` | `5000` |

O health check é o `HEALTHCHECK` do próprio `Dockerfile`: de 30 em 30 segundos (depois de 15 s de carência, e com limite de 5 s por tentativa), ele consulta `GET /healthz` dentro do container. A rota responde `200` com `{"status":"ok"}`, não pede login e não acessa banco nem dados. Se o seu painel de deploy pedir uma URL de health check, use `/healthz`: a `/api/status` exige login quando `DASHBOARD_PASSWORD` está definida e responderia `401`.

O workflow `docker.yml` monta as três imagens em todo PR que mexe nesses projetos, então um `Dockerfile` quebrado aparece no PR, e não no deploy.

> **Vai mudar na fase 3 da reorganização.** O monorepo está sendo reorganizado em fases numeradas (a lista e o registro de cada decisão estão em [decisoes.md](decisoes.md)). A fase 3 introduz o pacote `nucleo/`, com o código comum entre as loterias, e muda o Build Context dos painéis para a raiz do repositório: o Build Context passa a ser `/` e o Dockerfile passa a ser `<projeto>/Dockerfile`. Haverá aviso antes; até lá, vale a tabela acima.

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
| `DASHBOARD_MAX_JOBS` | só lotofacil | opcional | Teto de jobs pesados ao mesmo tempo (padrão `2`) |

O que cada uma faz e o que acontece se faltar:

- **`DASHBOARD_PASSWORD`**: exige login por senha em todas as rotas, menos `/healthz` e as páginas de login e logout. Sem ela **e** sem `DASHBOARD_PUBLICO=1`, o painel não inicia: o `gunicorn` reinicia o worker em loop, o log repete a mensagem que pede uma das duas variáveis e o container fica *unhealthy*. Uma variável vazia conta como ausente.
- **`DASHBOARD_PUBLICO`**: só vale o valor `1`. Confirma de propósito que o painel roda **sem senha**: quem alcançar a porta lê os dados e dispara trabalho. Use só atrás de rede ou túnel confiável. Se `DASHBOARD_PASSWORD` também estiver definida, o login continua exigido.
- **`DASHBOARD_AUTH_SECRET`**: chave fixa que assina a sessão de login. Sem ela, a chave é sorteada a cada início: todo restart ou redeploy derruba os logins (o log avisa), e com mais de um worker do gunicorn o login falha de forma intermitente (os `Dockerfile` usam 1 worker). Gere uma com `python3 -c "import secrets; print(secrets.token_hex(32))"`.
- **`DASHBOARD_MAX_JOBS`** (só lotofacil): teto de jobs pesados (geração, treino, backtest) ao mesmo tempo. Padrão `2`. Acima do teto, a API responde `429` em vez de enfileirar.

## Subir localmente com o Docker Compose

O [`docker-compose.yml`](../docker-compose.yml) da raiz monta os três painéis com os mesmos `Dockerfile` do EasyPanel. Exige o Docker Compose 2.24 ou mais novo.

1. Crie, na raiz do repositório, um arquivo `.env` com as variáveis da seção anterior. O git o ignora; nunca o versione.

   ```bash
   printf 'DASHBOARD_PASSWORD=%s\nDASHBOARD_AUTH_SECRET=%s\n' 'troque-esta-senha' "$(python3 -c 'import secrets; print(secrets.token_hex(32))')" > .env
   ```

   O `>` **sobrescreve** um `.env` que já exista: se você já tem um, edite-o à mão em vez de rodar o comando. `troque-esta-senha` é só um exemplo; escolha uma senha sua e não use a do exemplo de verdade.

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

- **O painel não abre e o container fica `unhealthy`.** Falta `DASHBOARD_PASSWORD` ou `DASHBOARD_PUBLICO=1` (ou o valor de `DASHBOARD_PUBLICO` não é exatamente `1`). O log (`docker compose logs megasena`) repete a mensagem que pede uma das duas. No compose, confira que o `.env` está na raiz do repositório.
- **O login cai a cada restart ou redeploy.** Falta `DASHBOARD_AUTH_SECRET`.
- **`Permission denied` ao gravar em `/app/dados` ou `/app/saida`.** O volume pertence a root, por exemplo porque foi criado por uma imagem antiga, que não tinha `USER`. Corrija o dono com `docker run --rm -v <volume>:/v alpine chown -R 1000:1000 /v`. O contexto está no [CHANGELOG](../CHANGELOG.md).
- **A API da lotofacil responde `429`.** Já há jobs pesados demais em andamento: espere um terminar ou aumente `DASHBOARD_MAX_JOBS`.
