# Onda 7 — Pastas físicas (dados/ + saida/)

**Prioridade:** média
**Risco:** médio (move artefatos grandes — `.keras`, JSONs históricos)
**Tasks:** 7
**Pré-requisitos:** Onda 6

## Objetivo

Consolidar todas as pastas físicas de input/output em duas raízes: `dados/` (entrada — symlink → `~/lotofacil-dados/`) e `saida/` (saída). Eliminar `data/`, `output/`, `src/models_saved/`, `src/lotofacil_lab/output/` (já está em `experimentos/`), etc.

## Estrutura final

```
lotofacil/
├── dados/                          # symlink → ~/lotofacil-dados/ (preservado)
│   ├── concursos/                  # JSONs da API CAIXA
│   ├── processado/                 # CSVs/Parquets derivados
│   └── lotofacil.db                # SQLite único
└── saida/
    ├── jogos/                      # portfolios + jogos formato apostável
    ├── predicoes/                  # JSON com confianças
    ├── modelos/                    # .keras, .joblib (de todos os trains)
    ├── relatorios/                 # backtests, HTML, KPI
    ├── experimentos/               # outputs do lab
    │   ├── modelos/                # .keras do lab
    │   ├── relatorios/             # ablation results
    │   └── ...
    └── logs/                       # logs runtime
```

## Movimentações

| De | Para | Operação |
|---|---|---|
| `data/raw/concursos/*.json` | `dados/concursos/` | `git mv` (preservar conteúdo do symlink) |
| `data/processed/all_draws.json` | `dados/processado/all_draws.json` | `git mv` |
| `data/lotofacil.db` | `dados/lotofacil.db` | `git mv` |
| `output/models/*.keras` | `saida/modelos/` | `git mv` |
| `output/predictions/` | `saida/predicoes/` | `git mv` |
| `output/reports/` | `saida/relatorios/` | `git mv` |
| `src/models_saved/` | `saida/modelos/` | `git mv` (consolida) |
| `src/lotofacil/experimentos/saved_models/` (ex-`lotofacil_lab/saved_models/`) | `saida/experimentos/modelos/` | `git mv` |
| `src/lotofacil/experimentos/output/` | `saida/experimentos/` | `git mv` |
| `saida/jogos_otimizados/jogos_otimizados.json` | `saida/jogos/jogos_otimizados.json` | `git mv` |
| `saida/sugestao/sugestao_*.{json,txt}` | `saida/jogos/sugestao_*.{json,txt}` | `git mv` |
| `logs/` | `saida/logs/` | `git mv` |

## Símbolo `dados/`

O symlink `dados/ → ~/lotofacil-dados/` é preservado. Quando movemos `data/raw/concursos/*` para `dados/concursos/`, o conteúdo vai parar fisicamente em `~/lotofacil-dados/concursos/`. Garantir que o destino existe antes do `git mv`:

```bash
mkdir -p ~/lotofacil-dados/concursos
mkdir -p ~/lotofacil-dados/processado
```

## Atualização de `infra/config.py`

```python
# Paths consolidados — single source of truth
PROJETO_RAIZ = Path(__file__).resolve().parent.parent.parent.parent
DADOS_DIR = PROJETO_RAIZ / "dados"
SAIDA_DIR = PROJETO_RAIZ / "saida"

CONCURSOS_DIR = DADOS_DIR / "concursos"
PROCESSADO_DIR = DADOS_DIR / "processado"
DB_PATH = DADOS_DIR / "lotofacil.db"

JOGOS_DIR = SAIDA_DIR / "jogos"
PREDICOES_DIR = SAIDA_DIR / "predicoes"
MODELOS_DIR = SAIDA_DIR / "modelos"
RELATORIOS_DIR = SAIDA_DIR / "relatorios"
EXPERIMENTOS_SAIDA_DIR = SAIDA_DIR / "experimentos"
LOGS_DIR = SAIDA_DIR / "logs"
```

Substitui as constantes antigas (`DATA_DIR`, `MODELS_DIR`, etc.) — atualizar todos os usos em `infra/`, `servicos/`, `interface/`, `experimentos/`.

## Tasks

1. `01-consolidar-dados.md` — `data/raw/concursos`, `data/processed`, `data/lotofacil.db` → `dados/`
2. `02-consolidar-modelos.md` — `output/models` + `src/models_saved` → `saida/modelos/`
3. `03-consolidar-predicoes-relatorios.md` — `output/predictions` → `saida/predicoes/`; `output/reports` → `saida/relatorios/`
4. `04-consolidar-experimentos.md` — `experimentos/saved_models` + `experimentos/output` → `saida/experimentos/`
5. `05-consolidar-jogos.md` — `saida/jogos_otimizados` + `saida/sugestao` → `saida/jogos/`
6. `06-mover-logs.md` — `logs/` → `saida/logs/`
7. `07-atualizar-config-paths.md` — `infra/config.py` + todas as referências

## Critérios de aceite (onda inteira)

- [ ] `pytest` passa
- [ ] `ls -la dados/` mostra `concursos/`, `processado/`, `lotofacil.db`
- [ ] `ls -la saida/` mostra `jogos/`, `predicoes/`, `modelos/`, `relatorios/`, `experimentos/`, `logs/`
- [ ] `find . -maxdepth 2 -type d -name "data" -o -name "output" -o -name "models_saved"` retorna 0
- [ ] `lotofacil dados status` retorna total correto (mesma base de dados)
- [ ] `lotofacil prever` salva em `saida/predicoes/` (não em `output/predictions/`)
- [ ] `lotofacil modelo treinar` salva em `saida/modelos/`
- [ ] Painel `/api/games`, `/api/models/status` retornam conteúdo

## Smoke test

```bash
pytest
ls -la dados/ saida/
test ! -d data/ && test ! -d output/ && test ! -d src/models_saved/ && echo "limpo"
lotofacil dados status
lotofacil prever              # gera em saida/predicoes/
ls saida/predicoes/
```
