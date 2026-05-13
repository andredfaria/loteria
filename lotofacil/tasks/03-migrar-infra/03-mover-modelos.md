# Task 3.3 — Mover `modelos/`, `agendador/` e `relatorio`

**Onda:** 3 — Migrar infra
**Prioridade:** alta
**Tempo estimado:** ~30 min
**Depende de:** 3.2

## Objetivo

Mover três pacotes de `lotofacil_ml/` simultaneamente (são conectados):

1. `lotofacil_ml/models/` → `infra/modelos/`
2. `lotofacil_ml/scheduler/` → `infra/agendador/`
3. `lotofacil_ml/report/` → `infra/avaliacao/relatorio.py` (ou pacote, dependendo do conteúdo)

## Descrição técnica

`lotofacil_ml/models/` contém `FrequencyModel`, `MLEnsembleModel`, `LSTMModel`, `EnsemblePredictor`, etc. — todo o stack de ML.

`scheduler/` é APScheduler para update/retrain automáticos.

`report/` gera HTML pós-backtest.

## Arquivos envolvidos

**Mover (modelos/):**

| De | Para |
|---|---|
| `src/lotofacil_ml/models/base.py` | `src/lotofacil/infra/modelos/base.py` |
| `src/lotofacil_ml/models/frequency_model.py` | `src/lotofacil/infra/modelos/frequencia.py` |
| `src/lotofacil_ml/models/frequency_ensemble.py` | `src/lotofacil/infra/modelos/frequencia_ensemble.py` |
| `src/lotofacil_ml/models/probabilistic.py` | `src/lotofacil/infra/modelos/probabilistico.py` |
| `src/lotofacil_ml/models/ml_ensemble.py` | `src/lotofacil/infra/modelos/ensemble_ml.py` |
| `src/lotofacil_ml/models/lstm_model.py` | `src/lotofacil/infra/modelos/lstm.py` |
| `src/lotofacil_ml/models/ensemble.py` | `src/lotofacil/infra/modelos/preditor_ensemble.py` |

(Ajustar à lista real após `ls`.)

**Mover (agendador/):**

| De | Para |
|---|---|
| `src/lotofacil_ml/scheduler/*.py` | `src/lotofacil/infra/agendador/*.py` (mesmos nomes ou PT) |

**Mover (report/):**

| De | Para |
|---|---|
| `src/lotofacil_ml/report/*.py` | `src/lotofacil/infra/avaliacao/relatorio.py` (consolidar em um arquivo se < 200 linhas; senão criar `infra/avaliacao/relatorio/`) |

**Renames de classes:**

| Antes | Depois |
|---|---|
| `BaseModel` | `ModeloBase` |
| `FrequencyModel` | `ModeloFrequencia` |
| `MLEnsembleModel` | `ModeloEnsembleML` |
| `LSTMModel` | mantém (acrônimo técnico) |
| `EnsemblePredictor` | `PreditorEnsemble` |
| `ReportGenerator` | `GeradorRelatorio` |

## Dependências

- 3.2 (`infra/atributos/` existe, `infra/dados/` existe)

## Critérios de aceite

- [ ] `from lotofacil.infra.modelos import ModeloFrequencia, ModeloEnsembleML, LSTMModel, PreditorEnsemble` funciona
- [ ] `from lotofacil.infra.agendador import <algo>` funciona
- [ ] `from lotofacil.infra.avaliacao.relatorio import GeradorRelatorio` funciona
- [ ] `grep -rn "from lotofacil_ml.models\|from lotofacil_ml.scheduler\|from lotofacil_ml.report" src/cli/ src/dashboard/` retorna 0
- [ ] `lotofacil modelo treinar` funciona (ou erra DB vazio)
- [ ] `pytest` passa

## Passos detalhados

- [ ] **Passo 1:** Listar arquivos

```bash
ls src/lotofacil_ml/models/ src/lotofacil_ml/scheduler/ src/lotofacil_ml/report/
```

- [ ] **Passo 2:** `git mv` em batch

```bash
# Modelos — ajuste a lista após inspeção
git mv src/lotofacil_ml/models/base.py src/lotofacil/infra/modelos/base.py
git mv src/lotofacil_ml/models/frequency_model.py src/lotofacil/infra/modelos/frequencia.py
# ... continue para cada arquivo

# Agendador
git mv src/lotofacil_ml/scheduler/ src/lotofacil/infra/agendador/_temp
mv src/lotofacil/infra/agendador/_temp/*.py src/lotofacil/infra/agendador/
rmdir src/lotofacil/infra/agendador/_temp

# Relatório (consolidar)
git mv src/lotofacil_ml/report/ src/lotofacil/infra/avaliacao/_report_temp
# Consolidar manualmente ou mover individual:
mv src/lotofacil/infra/avaliacao/_report_temp/*.py src/lotofacil/infra/avaliacao/
rmdir src/lotofacil/infra/avaliacao/_report_temp
# Renomear o principal:
git mv src/lotofacil/infra/avaliacao/generator.py src/lotofacil/infra/avaliacao/relatorio.py
```

- [ ] **Passo 3:** Renomear classes nos arquivos movidos

```bash
sed -i 's/class BaseModel\b/class ModeloBase/g' src/lotofacil/infra/modelos/*.py
sed -i 's/class FrequencyModel\b/class ModeloFrequencia/g' src/lotofacil/infra/modelos/*.py
sed -i 's/class MLEnsembleModel\b/class ModeloEnsembleML/g' src/lotofacil/infra/modelos/*.py
sed -i 's/class EnsemblePredictor\b/class PreditorEnsemble/g' src/lotofacil/infra/modelos/*.py
sed -i 's/class ReportGenerator\b/class GeradorRelatorio/g' src/lotofacil/infra/avaliacao/relatorio.py

# E referências internas (cuidado para não trocar em strings):
sed -i 's/\bBaseModel\b/ModeloBase/g' src/lotofacil/infra/modelos/*.py
sed -i 's/\bFrequencyModel\b/ModeloFrequencia/g' src/lotofacil/infra/modelos/*.py
sed -i 's/\bMLEnsembleModel\b/ModeloEnsembleML/g' src/lotofacil/infra/modelos/*.py
sed -i 's/\bEnsemblePredictor\b/PreditorEnsemble/g' src/lotofacil/infra/modelos/*.py
sed -i 's/\bReportGenerator\b/GeradorRelatorio/g' src/lotofacil/infra/avaliacao/relatorio.py
```

- [ ] **Passo 4:** Atualizar imports internos

Em `src/lotofacil/infra/modelos/*.py`:

```bash
sed -i 's|from lotofacil_ml\.models\.|from lotofacil.infra.modelos.|g' src/lotofacil/infra/modelos/*.py
sed -i 's|from lotofacil_ml\.features|from lotofacil.infra.atributos|g' src/lotofacil/infra/modelos/*.py
sed -i 's|from lotofacil_ml\.data\.|from lotofacil.infra.dados.|g' src/lotofacil/infra/modelos/*.py
sed -i 's|from lotofacil_ml\.config|from lotofacil.infra.config|g' src/lotofacil/infra/modelos/*.py
```

Repetir para `agendador/` e `relatorio.py`.

- [ ] **Passo 5:** Reescrever os `__init__.py`

`src/lotofacil/infra/modelos/__init__.py`:

```python
"""Camada de modelos de predição."""
from .base import ModeloBase
from .frequencia import ModeloFrequencia
from .frequencia_ensemble import FrequencyEnsembleModel  # mantém — provavelmente
from .probabilistico import ProbabilisticModel  # ajuste conforme rename
from .ensemble_ml import ModeloEnsembleML
from .preditor_ensemble import PreditorEnsemble

# LSTM é condicional (TensorFlow opcional)
try:
    from .lstm import LSTMModel
except ImportError:
    LSTMModel = None  # type: ignore[assignment, misc]

__all__ = [
    "ModeloBase",
    "ModeloFrequencia",
    "ModeloEnsembleML",
    "LSTMModel",
    "PreditorEnsemble",
]
```

`src/lotofacil/infra/agendador/__init__.py`:

```python
"""Agendador APScheduler — update Mon/Wed/Fri 23h, retrain Mon 2h."""
# Ajuste conforme conteúdo real do scheduler.
```

- [ ] **Passo 6:** Atualizar consumidores em CLI

```bash
sed -i \
  -e 's|from lotofacil_ml\.models\.|from lotofacil.infra.modelos.|g' \
  -e 's|from lotofacil_ml\.scheduler|from lotofacil.infra.agendador|g' \
  -e 's|from lotofacil_ml\.report|from lotofacil.infra.avaliacao|g' \
  -e 's|\bFrequencyModel\b|ModeloFrequencia|g' \
  -e 's|\bMLEnsembleModel\b|ModeloEnsembleML|g' \
  -e 's|\bEnsemblePredictor\b|PreditorEnsemble|g' \
  -e 's|\bReportGenerator\b|GeradorRelatorio|g' \
  src/cli/modelo.py src/cli/portfolio.py src/cli/app.py
```

- [ ] **Passo 7:** Validar imports

```bash
python -c "from lotofacil.infra.modelos import ModeloFrequencia, ModeloEnsembleML, PreditorEnsemble"
python -c "from lotofacil.infra.avaliacao.relatorio import GeradorRelatorio"
python -c "from cli.modelo import app"
```

- [ ] **Passo 8:** Verificar consumidores residuais

```bash
grep -rn "from lotofacil_ml.models\|from lotofacil_ml.scheduler\|from lotofacil_ml.report" src/cli/ src/dashboard/
# 0 esperado
```

- [ ] **Passo 9:** Testes

```bash
pytest
```

- [ ] **Passo 10:** Smoke

```bash
lotofacil modelo treinar
```

- [ ] **Passo 11:** Commit

```bash
git add -A
git commit -m "refactor(infra): move models/scheduler/report → infra/{modelos,agendador,avaliacao}

Renames PT:
- BaseModel → ModeloBase
- FrequencyModel → ModeloFrequencia
- MLEnsembleModel → ModeloEnsembleML
- EnsemblePredictor → PreditorEnsemble
- ReportGenerator → GeradorRelatorio
- LSTMModel mantido (acrônimo técnico)

Imports atualizados em cli/modelo.py, cli/portfolio.py, cli/app.py."
```
