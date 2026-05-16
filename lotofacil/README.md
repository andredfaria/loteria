# Lotofácil Prediction System

Sistema modular de predição para a Lotofácil (15 números sorteados de 1–25) com Machine Learning, redes neurais e dashboard web para treino e monitoramento.

> **Aviso:** Ferramenta de estudo estatístico. Loteria é jogo de azar — cada sorteio é um evento aleatório independente.

---

## Sumário

- [Instalação](#instalação)
- [CLI — Uso Rápido](#cli--uso-rápido)
- [Dashboard Web](#dashboard-web)
- [Arquitetura](#arquitetura)
- [Deploy com Docker](#deploy-com-docker)
- [Testes](#testes)

---

## Instalação

```bash
git clone https://github.com/andredfaria/loteria.git
cd loteria/lotofacil
python -m venv venv && source venv/bin/activate
pip install -e ".[dev]"
```

> Requer Python ≥ 3.12. TensorFlow é instalado automaticamente (necessário para treino neural).

---

## CLI — Uso Rápido

O entry point `lotofacil` é registrado via `pyproject.toml`.

```bash
# Dados
lotofacil dados atualizar             # sincroniza novos sorteios da API Caixa
lotofacil dados atualizar --escopo ultimo  # busca apenas o último sorteio
lotofacil dados status                # exibe total de sorteios e último concurso
lotofacil dados resetar               # apaga tudo e rebusca do concurso 1

# Modelos clássicos
lotofacil modelo treinar              # treina Frequency + ML ensemble + LSTM clássico
lotofacil modelo backtest             # walk-forward backtest

# Predição
lotofacil prever                      # ensemble de todas as abordagens
lotofacil prever --abordagem ml       # só LightGBM/RF
lotofacil prever --abordagem neural   # só LSTM clássico
lotofacil prever --abordagem statistical

# Portfolio
lotofacil portfolio --concurso <N>    # gera portfolio de 5 estratégias para o concurso N+1

# Experimentos (pipeline neural lab)
lotofacil lab train --config base+temp+priors
lotofacil lab train --config base+temp+priors+lua+clima --epochs 60
lotofacil lab predict --config base+temp+priors
lotofacil lab backfill-clima --ultimos 500
lotofacil lab lunar-check --data 2026-05-15
lotofacil lab ablation --n-test 100 --retrain-every 50
```

---

## Dashboard Web

O dashboard é uma aplicação Flask servida pelo Gunicorn na porta **5000**. Permite operar o sistema inteiro a partir do navegador, sem precisar da CLI.

### Iniciando localmente

```bash
source venv/bin/activate
gunicorn lotofacil.interface.painel.server:app \
  --bind 0.0.0.0:5000 \
  --workers 2 \
  --timeout 600
```

Acesse `http://localhost:5000`.

### Funcionalidades do Dashboard

#### Aba: Dados
- Visualiza sorteios históricos com paginação
- Exibe dados climáticos e fase lunar por concurso
- Botões para **Atualizar Base**, **Buscar Último**, **Status do DB** e **Resetar**

#### Aba: Predição
- Executa treinos neurais (LSTM + Attention) com configuração por interface:
  - Escolha de features: base, lua, clima, combinações
  - Parâmetros: epochs, seed, window size
  - Acompanha output em tempo real via polling
- Lista modelos treinados com métricas (val_loss, epochs)
- Gera jogos a partir de modelos salvos
- Compara dois modelos lado a lado

#### Aba: Resultados
- Lista predições geradas com acertos reais
- Métricas por abordagem: mean_hits, improvement_pct, p-value
- Gráficos de tendência e calibração de confiança

#### Console de log
- Exibe output de cada comando linha por linha
- Funciona por polling HTTP a cada 2s — sem SSE, funciona com múltiplos workers

### API REST do Dashboard

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `GET` | `/api/status` | Último concurso e totais |
| `GET` | `/api/commands` | Lista de comandos disponíveis |
| `POST` | `/api/generate` | Inicia um comando genérico (coleta, predição) |
| `GET` | `/api/jobs/<id>/poll?offset=N` | Polling de output de job em andamento |
| `GET` | `/api/dados?page=N&per_page=M` | Sorteios históricos paginados |
| `GET` | `/api/predictions` | Predições agrupadas por concurso |
| `GET` | `/api/models/status` | Modelos `.keras` salvos em disco |
| `GET` | `/api/models/quality` | Métricas comparativas por abordagem |
| `POST` | `/api/treinos/iniciar` | Inicia treino neural e registra no SQLite |
| `GET` | `/api/treinos` | Lista histórico de treinos |
| `GET` | `/api/treinos/<id>` | Detalhe de um treino |
| `POST` | `/api/treinos/<id>/gerar` | Gera jogos a partir de um modelo treinado |

### Sistema de Jobs (polling)

Comandos longos (treino neural, coleta completa) rodam em threads separadas. O output é gravado linha a linha em SQLite (`saida/treinos.db`, tabela `job_output`). O frontend faz polling a cada 2 segundos:

```
POST /api/treinos/iniciar  →  { treino_id, task_id }
GET  /api/jobs/<task_id>/poll?offset=0  →  { lines, done, next_offset }
GET  /api/jobs/<task_id>/poll?offset=N  →  { lines, done, success, next_offset }
```

Isso permite múltiplos workers Gunicorn sem estado em memória compartilhada.

---

## Arquitetura

```
lotofacil/
├── src/lotofacil/
│   ├── dominio/           # Entidades, regras de negócio, exceções
│   │   ├── entidades.py   # Sorteio, Jogo
│   │   └── regras.py      # Filtros estatísticos (pares, moldura, primos…)
│   │
│   ├── infra/
│   │   ├── config.py      # Paths centralizados: DADOS_DIR, SAIDA_DIR, MODELOS_DIR…
│   │   ├── avaliacao/     # Métricas, backtest walk-forward, significância estatística
│   │   └── dados/         # Fetcher API Caixa, persistência JSON
│   │
│   ├── servicos/          # Casos de uso (um arquivo por operação)
│   │   ├── atualizar_base.py
│   │   ├── treinar_modelos.py
│   │   ├── gerar_predicao.py
│   │   ├── gerar_portfolio.py
│   │   └── rodar_backtest.py
│   │
│   ├── interface/
│   │   ├── cli/           # CLI Typer (entry point: lotofacil)
│   │   │   ├── app.py     # Root app
│   │   │   ├── dados.py   # lotofacil dados …
│   │   │   ├── modelo.py  # lotofacil modelo …
│   │   │   ├── portfolio.py
│   │   │   └── lab.py     # lotofacil lab …
│   │   │
│   │   └── painel/        # Dashboard Web
│   │       ├── server.py         # Flask app + endpoints + _run_command
│   │       ├── commands.py       # Definição dos comandos do painel (cmd + cwd)
│   │       ├── treino_registry.py # SQLite: treinos + job_output + job_status
│   │       └── static/
│   │           └── dashboard.html # SPA vanilla JS — mobile-first
│   │
│   └── experimentos/      # Pipeline neural lab (LSTM + Attention + Focal Loss)
│       ├── main.py        # Entry point: lotofacil lab …
│       ├── config.py      # Paths e constantes do lab
│       ├── data/          # Loaders: sorteios, clima, lua, feature flags
│       ├── models/        # NeuralModular, baselines
│       └── experiments/   # Ablation grid, runner, report
│
├── dados/
│   └── sample/            # 100 sorteios mais recentes (committed)
├── saida/                 # Gerado em runtime (gitignored)
│   ├── jogos/             # JSONs de predições e jogos gerados
│   ├── modelos/           # Modelos clássicos (.joblib)
│   ├── logs/              # dashboard_server.log
│   └── treinos.db         # SQLite: treinos + job output
├── Dockerfile             # Imagem de produção (Python 3.12 + Gunicorn)
├── entrypoint.sh          # Cria estrutura de diretórios no volume
├── docker-compose.yml     # Para desenvolvimento local com volumes nomeados
└── pyproject.toml         # Dependências e entry point CLI
```

### Camadas

```
CLI / Dashboard (interface)
        ↓
    Serviços (casos de uso)
        ↓
  Domínio (regras e entidades)
        ↓
    Infra (config, dados, avaliação)
```

Paths são sempre resolvidos via `lotofacil.infra.config` — nunca relativos a `__file__` nas camadas superiores.

---

## Deploy com Docker

### Dockerfile correto

O `Dockerfile` em `lotofacil/` é o de produção. O `Dockerfile` na raiz do repositório `loteria/` é uma versão legada e **não deve ser usada**.

```dockerfile
# lotofacil/Dockerfile (produção)
FROM python:3.12-slim
RUN apt-get install -y gcc libgomp1   # libgomp1 necessário para TensorFlow
COPY pyproject.toml README.md ./
RUN pip install -e ".[dev]"           # instala tensorflow + gunicorn + tudo
COPY src/ src/
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", ..., "--workers", "2", "--timeout", "600"]
```

### Configuração no EasyPanel

| Campo | Valor |
|-------|-------|
| **Build Context** | `lotofacil` |
| **Dockerfile Path** | `lotofacil/Dockerfile` |
| **Port** | `5000` |

> Se apontar para o `Dockerfile` da raiz, o TensorFlow **não será instalado** e o servidor de desenvolvimento Flask será usado em vez do Gunicorn.

### Volumes necessários

Configure três volumes persistentes no EasyPanel (ou via `docker-compose.yml` localmente):

| Volume | Caminho no container | Conteúdo |
|--------|----------------------|----------|
| `lotofacil_dados` | `/app/dados` | Sorteios JSON, clima, lua |
| `lotofacil_saida` | `/app/saida` | Jogos gerados, modelos, logs, treinos.db |
| `lotofacil_lab_models` | `/app/src/lotofacil/experimentos/saved_models` | Modelos neurais `.keras` |

### Primeira execução

Após o deploy, abra o dashboard e clique em **Atualizar Base** para baixar o histórico completo de sorteios (concurso 1 → atual). O volume `dados` começa vazio — a imagem não semeia dados automaticamente.

---

## Testes

```bash
source venv/bin/activate

# Todos os testes
pytest -v

# Por módulo
pytest src/lotofacil/interface/painel/tests/ -v   # dashboard + registry
pytest testes/ -v                                  # testes de domínio e serviços
```

---

## Licença

MIT — veja [../LICENSE](../LICENSE).
