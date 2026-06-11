# CLAUDE.md

Guidance for Claude Code (and other AI assistants) working in this repository.

## Repository Overview

This is a **monorepo** of statistical analysis / ML systems for Brazilian lottery
games (Caixa Econômica Federal). It is a study project — nothing here guarantees
winnings, and code/docs should keep that framing.

| Subproject | Description | Status |
|---|---|---|
| `lotofacil/` | Full pipeline: data collection, stats, ML, neural lab, web dashboard | **Active** — most development happens here |
| `dia-de-sorte/` | Statistical analysis for Dia de Sorte | Paused (kept as reference) |
| `super-sete/` | Per-column data collection + statistical analysis | Active, lightweight |
| `megasena/` | Mega-Sena | Planned / not started (just a README) |

Each subproject is **self-contained** with its own `requirements.txt` or
`pyproject.toml` and (optionally) its own virtualenv. Don't assume shared
dependencies across subprojects.

All subprojects consume the same public API for historical draw data:
```
https://loteriascaixa-api.herokuapp.com/api/<loteria>/<concurso>
```
where `<loteria>` is `lotofacil`, `megasena`, `supersete`, etc.

## Language & Naming Conventions

- **User-facing docs, READMEs, commit messages, and CLI text are in
  Portuguese (PT-BR).** Code identifiers in `lotofacil/` follow the same
  convention — modules, classes, functions, CLI flags/commands are named in
  Portuguese (`Sorteio`, `Predicao`, `dominio/`, `servicos/`, `--abordagem`,
  `--concurso`, `lotofacil dados atualizar`, etc.).
- A handful of well-established technical loanwords are kept in English:
  `backtest`, `status`, `dataclass`, `Protocol`, `pipeline`.
- When adding new modules/classes/CLI flags to `lotofacil/`, follow this
  Portuguese-naming convention for consistency with the rest of the codebase.
- Code comments and docstrings in `lotofacil/` are also generally PT-BR.

## Lotofácil — Architecture (the main subproject)

Layered architecture, paths always resolved via `lotofacil.infra.config`
(`PROJETO_RAIZ`, `DADOS_DIR`, `SAIDA_DIR`, `MODELOS_DIR`, etc.) — **never**
relative to `__file__` in upper layers.

```
CLI / Dashboard (interface)
        ↓
    Serviços (casos de uso)
        ↓
  Domínio (regras e entidades)
        ↓
    Infra (config, dados, avaliação, modelos, estratégias)
```

```
lotofacil/
├── src/lotofacil/
│   ├── dominio/            # Entidades (Sorteio, Jogo), regras de negócio, exceções
│   ├── infra/
│   │   ├── config.py       # Paths centralizados + constantes (modelo, premiação, schedule)
│   │   ├── dados/           # Fetcher API Caixa, leitura/persistência de sorteios
│   │   ├── atributos/       # Feature engineering (clássico)
│   │   ├── avaliacao/       # Métricas, backtest walk-forward, significância, relatórios
│   │   ├── modelos/         # Frequency, ML (LightGBM/RF), LSTM, ensemble, autoencoder, transformer
│   │   ├── estrategias/      # onze_dezenas/ e quinze_dezenas/ (predictors, post-processors)
│   │   └── agendador/       # APScheduler — atualização automática
│   ├── servicos/            # Casos de uso, um arquivo por operação
│   │   ├── atualizar_base.py, treinar_modelos.py, gerar_predicao.py
│   │   ├── gerar_portfolio.py, rodar_backtest.py, validar_portfolio.py
│   │   └── listar_*.py, consultar_status_base.py, validar_predicoes.py
│   ├── interface/
│   │   ├── cli/             # Typer CLI — entry point `lotofacil`
│   │   │   ├── app.py       # root app + `lotofacil prever`
│   │   │   ├── dados.py     # `lotofacil dados …`
│   │   │   ├── modelo.py    # `lotofacil modelo …`
│   │   │   ├── portfolio.py # `lotofacil portfolio …`
│   │   │   └── lab.py       # `lotofacil lab …` (neural lab pipeline)
│   │   └── painel/          # Flask dashboard (port 5000)
│   │       ├── server.py         # app + REST endpoints + job runner (_run_command)
│   │       ├── commands.py       # comandos disponíveis no painel
│   │       ├── treino_registry.py # SQLite: treinos + job_output + job_status
│   │       └── static/dashboard.html  # SPA vanilla JS, mobile-first
│   └── experimentos/        # "Neural Lab" — LSTM + Attention + Focal Loss, features exógenas
│       ├── main.py           # entry point for `lotofacil lab`
│       ├── config.py         # paths/constants for the lab
│       ├── data/              # loaders: sorteios, clima (Open-Meteo), lua, feature flags
│       ├── features/          # builders: temporal, lunar, climate, interactions, similarity, priors
│       ├── models/             # NeuralModular, baselines (random, frequency)
│       ├── evaluation/         # metrics, walkforward, permutation importance
│       ├── coleta/              # backfill de dados climáticos
│       └── experiments/        # ablation grid, runner, report
├── dados/sample/             # 100 most recent draws, committed (works without full sync)
├── saida/                     # Runtime output (gitignored): jogos/, modelos/, logs/, treinos.db
├── testes/                     # Domain & service tests (pytest, testpaths)
│   ├── unidade/{dominio,servicos,infra,experimentos}/
│   └── integracao/cli/
├── tasks/                       # Historical refactor plan (executed, mostly informational)
├── docs/                         # Architecture, strategy docs, dashboard, dataset dictionary
├── Dockerfile                    # PRODUCTION image (Python 3.12 + Gunicorn + TensorFlow)
├── entrypoint.sh
├── docker-compose.yml
└── pyproject.toml
```

### Important: tests live in two places

- `lotofacil/testes/` — domain/service/CLI tests, run via `pytest` (configured
  as `testpaths` in `pyproject.toml`).
- `lotofacil/src/lotofacil/interface/painel/tests/` and
  `lotofacil/src/lotofacil/experimentos/tests/` — co-located tests for the
  dashboard and the neural lab.

Run everything with `pytest -v` from `lotofacil/`, or target a subset:
```bash
pytest testes/ -v
pytest src/lotofacil/interface/painel/tests/ -v
pytest src/lotofacil/experimentos/tests/ -v
```

## Setup & Common Commands (lotofacil)

```bash
cd lotofacil
python -m venv venv && source venv/bin/activate
pip install -e ".[dev]"        # requires Python >= 3.11 (Docker uses 3.12); installs TensorFlow
```

CLI entry point `lotofacil` (Typer), registered via `pyproject.toml`:

```bash
lotofacil dados atualizar              # sync new draws from Caixa API
lotofacil dados atualizar --escopo ultimo
lotofacil dados status
lotofacil dados resetar                # wipe + refetch from concurso 1

lotofacil modelo treinar               # train Frequency + ML ensemble + classic LSTM
lotofacil modelo backtest              # walk-forward backtest

lotofacil prever                       # ensemble prediction for next concurso
lotofacil prever --abordagem ml
lotofacil prever --abordagem neural
lotofacil prever --abordagem statistical

lotofacil portfolio --concurso <N>     # generate 5-strategy portfolio for N+1

# Neural lab (experimentos)
lotofacil lab train --config base+temp+priors
lotofacil lab train --config base+temp+priors+lua+clima --epochs 60
lotofacil lab predict --config base+temp+priors
lotofacil lab backfill-clima --ultimos 500
lotofacil lab lunar-check --data 2026-05-15
lotofacil lab ablation --n-test 100 --retrain-every 50
```

### Dashboard (Flask + Gunicorn, port 5000)

```bash
gunicorn lotofacil.interface.painel.server:app \
  --bind 0.0.0.0:5000 --workers 2 --timeout 600
```

Long-running commands (neural training, full data sync) run in background
threads; output is streamed line-by-line to SQLite (`saida/treinos.db`,
table `job_output`) and polled by the frontend every 2s
(`GET /api/jobs/<task_id>/poll?offset=N`) — this design supports multiple
Gunicorn workers without shared in-memory state. Don't reintroduce
SSE/websockets here without good reason.

## Docker / Deploy — IMPORTANT GOTCHA

There are **two Dockerfiles**:
- `lotofacil/Dockerfile` — **production**, Python 3.12, installs `.[dev]`
  (includes TensorFlow + Gunicorn). This is what EasyPanel must use.
- `/Dockerfile` (repo root) — **legacy**, excludes TensorFlow, uses Flask's
  dev server. **Do not use for deploys.**

EasyPanel config must be: Build Context = `lotofacil`, Dockerfile Path =
`Dockerfile`, Port = `5000`. Three persistent volumes are required:
`dados/`, `saida/`, and `src/lotofacil/experimentos/saved_models/`.

## Key Conventions

- **Paths**: always via `lotofacil.infra.config` constants — never
  `os.getcwd()` or ad-hoc `Path(__file__)` resolution outside `infra/`.
- **No data leakage**: features/predictions for draw `t` must only use
  `draws[:t]` (strictly past data). This applies to both the classic
  pipeline (`infra/atributos`) and the neural lab (`experimentos/features`).
- **Constants/config** (model hyperparameters, prize table, schedule) live in
  `lotofacil/src/lotofacil/infra/config.py` — don't hardcode magic numbers
  elsewhere. Note this file currently contains both PT-BR names and English
  aliases (`TOTAL_NUMBERS = TOTAL_NUMEROS`, etc.) for backward compatibility
  with older code — prefer the PT-BR names in new code.
- **Sample data**: `dados/sample/` (and equivalents in other subprojects)
  contains the 100 most recent draws so the system is usable without a full
  data sync.
- **Domain types are Pydantic** (`dominio/entidades.py`): `Sorteio`, `Jogo`.

## Other Subprojects

### Super Sete (`super-sete/`)
```bash
cd super-sete
pip install -r requirements.txt
python busca_sorteios.py        # collect draws → dados_supersete/concurso_<N>.json
python analise_estatistica.py   # per-column composite score (frequency, delay, trend, entropy, diversity)
```

### Dia de Sorte (`dia-de-sorte/`)
Paused; analysis script is `analisar_diadesorte.py` with sample data in
`dados/sample/` and tests in `tests/`. Treat as reference-only unless asked
to actively work on it.

### Mega-Sena (`megasena/`)
Just a placeholder README — not implemented.
