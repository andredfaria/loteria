# Onda 3 — Migrar infra

**Prioridade:** alta
**Risco:** médio-alto (mexe em muitos imports)
**Tasks:** 5
**Pré-requisitos:** Onda 2

## Objetivo

Mover as implementações canônicas (de `src/lotofacil_ml/` na maior parte) para `src/lotofacil/infra/<capacidade>/`, atualizando **no mesmo commit** todos os imports em `src/cli/*.py` que apontam para os locais antigos. Resíduos vazios deixados para a onda 5 deletar.

## Onde cada coisa vai

| De | Para |
|---|---|
| `src/lotofacil_ml/data/` | `src/lotofacil/infra/dados/` |
| `src/data/preprocessor.py` (único) | `src/lotofacil/infra/dados/preprocessador.py` |
| `src/lotofacil_ml/features/` | `src/lotofacil/infra/atributos/` |
| `src/lotofacil_ml/models/` | `src/lotofacil/infra/modelos/` |
| `src/lotofacil_ml/scheduler/` | `src/lotofacil/infra/agendador/` |
| `src/lotofacil_ml/report/` | `src/lotofacil/infra/avaliacao/relatorio.py` |
| `src/lotofacil_ml/{evaluation,backtest}/` | `src/lotofacil/infra/avaliacao/` |
| `src/evaluation/comparison.py` (único canônico) | `src/lotofacil/infra/avaliacao/comparacao.py` |
| `src/strategies/eleven_numbers/`, `quinze_numbers/`, `future/twelve_numbers/`, `future/thirteen_numbers/`, `future/fourteen_numbers/` | `src/lotofacil/infra/estrategias/{onze,quinze,doze,treze,quatorze}_dezenas/` |
| `src/strategies/base.py` | já está em `src/lotofacil/dominio/estrategia.py` (onda 2) — apagar `base.py` |

## Imports a atualizar (já no mesmo commit)

- `src/cli/dados.py` — qualquer `from lotofacil_ml.*` → `from lotofacil.infra.*`
- `src/cli/modelo.py` — todos os `from lotofacil_ml.data.*`, `from lotofacil_ml.models.*`, `from lotofacil_ml.backtest.*` → `from lotofacil.infra.*`
- `src/cli/portfolio.py` — idem
- `src/cli/app.py` — `from data.loader import ...` → `from lotofacil.infra.dados.leitor import ...`; `from strategies.eleven_numbers.predictor import ElevenNumbersStrategy` → `from lotofacil.infra.estrategias.onze_dezenas.predictor import EstrategiaOnzeDezenas` (renomear classe também)
- `src/dashboard/server.py` — qualquer import antigo que use `lotofacil_ml.*` ou similar
- `src/lotofacil_lab/` — atualizar **só** os imports do core (não move o lab ainda)

## Renames de classes durante a movimentação

Algumas classes ganham nome PT no caminho:

| EN antigo | PT novo |
|---|---|
| `ElevenNumbersStrategy` | `EstrategiaOnzeDezenas` |
| `BaseStrategy` | já é `EstrategiaBase` (em `dominio/estrategia.py`) |
| `DatabaseManager` | mantém (consagrado) ou `GerenciadorBanco`? — **mantém DatabaseManager** (loanword) |
| `LotofacilFetcher` | `ColetorAPI` |
| `LotofacilPreprocessor` | `Preprocessador` |
| `FrequencyModel` | `ModeloFrequencia` |
| `MLEnsembleModel` | `ModeloEnsembleML` |
| `LSTMModel` | mantém (acrônimo) |
| `EnsemblePredictor` | `PreditorEnsemble` |
| `BacktestEngine` / `BacktestSummary` | mantém `backtest` (loanword), classes: `Backtester` e `ResumoBacktest` |
| `LotofacilMetrics` | `Metricas` |
| `WalkForwardValidator` | mantém (termo técnico) |
| `ReportGenerator` | `GeradorRelatorio` |

Convenção: loanwords técnicos (`backtest`, `ensemble`, `LSTM`, `walk-forward`) ficam; vocabulário comum (`fetcher`, `preprocessor`, `database`) traduz.

## Tasks

1. `01-mover-dados.md` — dados/ (canonical) + atualizar imports
2. `02-mover-atributos.md` — atributos/ + imports
3. `03-mover-modelos.md` — modelos/ + agendador/ + relatorio (3 movimentações)
4. `04-mover-avaliacao.md` — avaliacao/ + comparacao + walk_forward + metricas
5. `05-mover-estrategias.md` — estrategias/ + renames + atualizar `cli/app.py prever`

## Critérios de aceite (onda inteira)

- [ ] `pytest` passa
- [ ] `lotofacil dados status` funciona
- [ ] `lotofacil prever` funciona
- [ ] `lotofacil modelo treinar` funciona (ou erra "DB vazio" — esperado se sem dados)
- [ ] `lotofacil portfolio --jogos 4` funciona
- [ ] `lotofacil lab ablation --n-test 10` funciona
- [ ] **Nenhum** `from lotofacil_ml.*` em `src/cli/`, `src/dashboard/` (use `grep -rn "from lotofacil_ml" src/cli/ src/dashboard/`)

## Smoke test

```bash
pytest
grep -rn "from lotofacil_ml\|from strategies\|from data\." src/cli/ src/dashboard/
# Deve retornar 0 resultados (todos migrados)

lotofacil dados status
lotofacil prever
```

## Estratégia de mitigação de risco

- Cada task move um **conjunto coerente** e atualiza imports correspondentes no mesmo commit
- Antes do commit, rodar `python -c "from lotofacil.interface.cli.app import app"` (ainda não existe — usar `python -c "from cli.app import app"` enquanto interface não está movida)
- `git mv` em vez de `mv` + `git add` para preservar histórico
- `pytest` antes E depois de cada task
- Se quebrar: `git reset --hard HEAD` (não comitou ainda) ou `git revert HEAD` (já comitou)
