# Task 3.4 — Mover `avaliacao/` (backtest, métricas, walk-forward, comparação)

**Onda:** 3 — Migrar infra
**Prioridade:** alta
**Tempo estimado:** ~25 min
**Depende de:** 3.3

## Objetivo

Mover os pacotes `lotofacil_ml/evaluation/` e `lotofacil_ml/backtest/` para `infra/avaliacao/`. Trazer também `src/evaluation/comparison.py` (canônico único de comparação) que ficou na árvore órfã.

## Descrição técnica

`lotofacil_ml/evaluation/` contém `LotofacilMetrics`, `WalkForwardValidator`.
`lotofacil_ml/backtest/` contém `BacktestEngine`, `BacktestSummary`, `baseline.py`.
`src/evaluation/comparison.py` (não no lotofacil_ml) é a única implementação canônica de comparação de abordagens.

## Arquivos envolvidos

**Mover:**

| De | Para |
|---|---|
| `src/lotofacil_ml/evaluation/metrics.py` | `src/lotofacil/infra/avaliacao/metricas.py` |
| `src/lotofacil_ml/evaluation/walk_forward.py` | `src/lotofacil/infra/avaliacao/walk_forward.py` (mantém — termo técnico) |
| `src/lotofacil_ml/backtest/engine.py` | `src/lotofacil/infra/avaliacao/backtest.py` |
| `src/lotofacil_ml/backtest/baseline.py` | `src/lotofacil/infra/avaliacao/baseline.py` |
| `src/lotofacil_ml/backtest/financial.py` | `src/lotofacil/infra/avaliacao/financeiro.py` |
| `src/evaluation/comparison.py` | `src/lotofacil/infra/avaliacao/comparacao.py` |

(Ajustar conforme `ls` revelar.)

**Renames de classes:**

| Antes | Depois |
|---|---|
| `LotofacilMetrics` | `Metricas` |
| `WalkForwardValidator` | mantém |
| `BacktestEngine` | `Backtester` |
| `BacktestSummary` | `ResumoBacktest` |
| `FinancialSimulator` | `SimuladorFinanceiro` |

## Dependências

- 3.3

## Critérios de aceite

- [ ] `from lotofacil.infra.avaliacao import Metricas, WalkForwardValidator, Backtester, ResumoBacktest` funciona
- [ ] `from lotofacil.infra.avaliacao.comparacao import comparar_abordagens` (ou nome equivalente) funciona
- [ ] `grep -rn "from lotofacil_ml.evaluation\|from lotofacil_ml.backtest" src/cli/ src/dashboard/` retorna 0
- [ ] `lotofacil modelo backtest` funciona
- [ ] `lotofacil modelo validar` funciona
- [ ] `pytest` passa

## Passos detalhados

- [ ] **Passo 1:** Listar arquivos

```bash
ls src/lotofacil_ml/evaluation/ src/lotofacil_ml/backtest/ src/evaluation/
```

- [ ] **Passo 2:** `git mv` em batch

```bash
git mv src/lotofacil_ml/evaluation/metrics.py src/lotofacil/infra/avaliacao/metricas.py
git mv src/lotofacil_ml/evaluation/walk_forward.py src/lotofacil/infra/avaliacao/walk_forward.py
git mv src/lotofacil_ml/backtest/engine.py src/lotofacil/infra/avaliacao/backtest.py
git mv src/lotofacil_ml/backtest/baseline.py src/lotofacil/infra/avaliacao/baseline.py
git mv src/lotofacil_ml/backtest/financial.py src/lotofacil/infra/avaliacao/financeiro.py 2>/dev/null  # pode não existir
git mv src/evaluation/comparison.py src/lotofacil/infra/avaliacao/comparacao.py
# Outros __init__.py mesclados manualmente
```

- [ ] **Passo 3:** Renomear classes

```bash
sed -i \
  -e 's/class LotofacilMetrics\b/class Metricas/g' \
  -e 's/\bLotofacilMetrics\b/Metricas/g' \
  -e 's/class BacktestEngine\b/class Backtester/g' \
  -e 's/\bBacktestEngine\b/Backtester/g' \
  -e 's/class BacktestSummary\b/class ResumoBacktest/g' \
  -e 's/\bBacktestSummary\b/ResumoBacktest/g' \
  -e 's/class FinancialSimulator\b/class SimuladorFinanceiro/g' \
  -e 's/\bFinancialSimulator\b/SimuladorFinanceiro/g' \
  src/lotofacil/infra/avaliacao/*.py
```

- [ ] **Passo 4:** Atualizar imports internos

```bash
sed -i \
  -e 's|from lotofacil_ml\.evaluation\.|from lotofacil.infra.avaliacao.|g' \
  -e 's|from lotofacil_ml\.backtest\.|from lotofacil.infra.avaliacao.|g' \
  -e 's|from lotofacil_ml\.models\.|from lotofacil.infra.modelos.|g' \
  -e 's|from lotofacil_ml\.features|from lotofacil.infra.atributos|g' \
  -e 's|from lotofacil_ml\.data\.|from lotofacil.infra.dados.|g' \
  -e 's|from lotofacil_ml\.config|from lotofacil.infra.config|g' \
  src/lotofacil/infra/avaliacao/*.py
```

- [ ] **Passo 5:** Escrever `src/lotofacil/infra/avaliacao/__init__.py`

```python
"""Camada de avaliação — backtest, métricas, walk-forward, comparação."""
from .metricas import Metricas
from .walk_forward import WalkForwardValidator
from .backtest import Backtester, ResumoBacktest
from .comparacao import comparar_abordagens  # ajustar se função tem outro nome

__all__ = [
    "Metricas",
    "WalkForwardValidator",
    "Backtester",
    "ResumoBacktest",
    "comparar_abordagens",
]
```

- [ ] **Passo 6:** Atualizar CLI

```bash
sed -i \
  -e 's|from lotofacil_ml\.evaluation\.|from lotofacil.infra.avaliacao.|g' \
  -e 's|from lotofacil_ml\.backtest\.|from lotofacil.infra.avaliacao.|g' \
  -e 's|from src\.evaluation\.|from lotofacil.infra.avaliacao.|g' \
  -e 's|from evaluation\.|from lotofacil.infra.avaliacao.|g' \
  -e 's|\bLotofacilMetrics\b|Metricas|g' \
  -e 's|\bBacktestEngine\b|Backtester|g' \
  -e 's|\bBacktestSummary\b|ResumoBacktest|g' \
  -e 's|\bFinancialSimulator\b|SimuladorFinanceiro|g' \
  src/cli/modelo.py src/cli/portfolio.py src/cli/app.py
```

- [ ] **Passo 7:** Validar imports

```bash
python -c "from lotofacil.infra.avaliacao import Metricas, Backtester, ResumoBacktest, WalkForwardValidator"
python -c "from cli.modelo import app"
```

- [ ] **Passo 8:** Verificar residuais

```bash
grep -rn "from lotofacil_ml.evaluation\|from lotofacil_ml.backtest\|from src.evaluation\|from evaluation\." src/cli/ src/dashboard/
# 0 esperado
```

- [ ] **Passo 9:** Testes

```bash
pytest
```

- [ ] **Passo 10:** Smoke

```bash
lotofacil modelo backtest
lotofacil modelo validar
```

- [ ] **Passo 11:** Commit

```bash
git add -A
git commit -m "refactor(infra): consolida avaliação em infra/avaliacao

Move:
- lotofacil_ml/evaluation/metrics.py → metricas.py (LotofacilMetrics → Metricas)
- lotofacil_ml/evaluation/walk_forward.py → walk_forward.py (mantém)
- lotofacil_ml/backtest/engine.py → backtest.py (BacktestEngine → Backtester)
- lotofacil_ml/backtest/baseline.py → baseline.py
- src/evaluation/comparison.py → comparacao.py (canônico único)

Imports atualizados em cli/modelo.py, cli/portfolio.py."
```
