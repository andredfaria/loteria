# Configurar os apps no EasyPanel (build com contexto na raiz)

Os `Dockerfile` de lotofacil, quina e megasena copiam o pacote compartilhado `nucleo/`, que fica na raiz do repositório, fora da pasta de cada projeto. Por isso o build precisa partir da **raiz do repositório**, e não da pasta do projeto. Se o EasyPanel continuar com a configuração antiga (contexto na pasta do projeto), todo build falha.

## Os dois campos que precisam mudar

No EasyPanel, cada app tem **dois campos separados**, em abas diferentes. Os dois precisam ser alterados:

| Aba | Campo | Valor antigo | Valor novo |
|-----|-------|--------------|------------|
| **Source → GitHub** | **Build Path** (contexto do build) | `/lotofacil` | `/` |
| **Build → Dockerfile** | **File** (caminho do Dockerfile) | `Dockerfile` | `lotofacil/Dockerfile` |

O caminho do Dockerfile é relativo à raiz do repositório. Para os outros apps, troque `lotofacil` por `quina` ou `megasena`:

| App | Build Path | Dockerfile (File) | Porta |
|-----|------------|-------------------|-------|
| lotofacil | `/` | `lotofacil/Dockerfile` | `5000` |
| quina | `/` | `quina/Dockerfile` | `5000` |
| megasena | `/` | `megasena/Dockerfile` | `5000` |

Volumes, porta e variáveis de ambiente **não mudam** (ver [deploy.md](../deploy.md)).

## Passo a passo

Repita para cada app (lotofacil, quina, megasena):

1. Abra o app no EasyPanel.
2. Aba **Source** → GitHub: mude **Build Path** para `/` e clique em **Save**.
3. Aba **Build** → Dockerfile: mude **File** para `<projeto>/Dockerfile` e clique em **Save**.
4. Clique em **Deploy**. O EasyPanel baixa o último commit da `main`, então não é preciso fazer um push novo.
5. Acompanhe o log do build (veja abaixo como confirmar que deu certo).

Enquanto o build novo não passa, o container que já está publicado continua servindo.

## Como ler o log do build

O começo do log mostra qual contexto o EasyPanel usou:

```
#3 [internal] load .dockerignore
#3 transferring context: 175B          ← contexto ERRADO (pasta do projeto)
```

```
#3 [internal] load .dockerignore
#3 transferring context: ~660B         ← contexto CERTO (raiz do repositório)
```

- **~175B**: o Docker leu a `.dockerignore` da pasta do projeto (`lotofacil/.dockerignore`). O **Build Path** ainda aponta para a pasta do projeto.
- **~660B**: o Docker leu a `.dockerignore` da raiz. O contexto está certo.

A linha `transferring dockerfile: 2.08kB` só mostra que o EasyPanel achou o Dockerfile. Ela pode estar certa mesmo com o contexto errado.

## Erro típico: `"/nucleo": not found`

```
#9 [ 4/12] COPY nucleo/ /opt/nucleo/
#9 ERROR: failed to calculate checksum of ref ...: "/nucleo": not found
...
ERROR: failed to build: ... "/lotofacil/entrypoint.sh": not found
```

**Causa:** o **Build Path** do app ainda é a pasta do projeto (`/lotofacil`). Dentro dela não existem `nucleo/` nem `lotofacil/src/`, que viraria `lotofacil/lotofacil/src/`. Por isso todos os `COPY` falham. Outro sinal é a linha `load build context … transferring context: 2B`: nada foi enviado.

**Correção:** **Source → GitHub → Build Path** = `/`, salve e faça o deploy de novo. Não é problema de código: fazer push de novo sem mudar esse campo dá o mesmo erro.

## Conferir localmente

O mesmo build que o EasyPanel faz, rodado na raiz do repositório:

```bash
docker build -f lotofacil/Dockerfile -t loteria-lotofacil .
```

O `.` no final é o contexto (a raiz). O workflow de CI `docker.yml` e o `docker-compose.yml` usam essa mesma forma.

## Uso de CPU

Os Dockerfiles limitam as threads de cálculo a 2 por processo (`OMP_NUM_THREADS`, `LOKY_MAX_CPU_COUNT` e afins), para que um treino não ocupe o servidor inteiro. Para um teto rígido, defina também o limite de CPU do app em **Advanced → Resources**. Detalhes em [deploy.md](../deploy.md), seção *Variáveis de ambiente*.
