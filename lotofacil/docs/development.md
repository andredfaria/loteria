# Guia de Desenvolvimento

## Setup

```bash
python -m venv venv && source venv/bin/activate
pip install -e ".[dev]"
```

## Comandos

```bash
# Coleta
python src/main.py collect --latest
python src/main.py collect --sync
python src/main.py collect --from 3500 --to 3700

# Processamento
python src/main.py process

# Predição
python src/main.py predict
python src/main.py predict --approach ml
python src/main.py predict --approach neural
python src/main.py predict --approach all

# Treino Neural
python src/main.py train-neural

# Avaliação
python src/main.py backtest
python src/main.py compare

# Status
python src/main.py status
```

## Testes

```bash
pytest tests/ -v
```

## Convenções

- Todos os scripts resolvem paths via `Path(__file__)`, nunca `os.getcwd()`
- Use `core.config` como fonte única de constantes e paths
- Modelos de dados são Pydantic em `core/models.py`
- Features sem data leakage: sempre use apenas `draws[:idx]`

## Adicionar nova estratégia

```python
from strategies.base import BaseStrategy

class MyStrategy(BaseStrategy):
    @property
    def name(self) -> str:
        return "my-strategy"

    @property
    def target_count(self) -> int:
        return 12

    @property
    def approaches(self) -> list[str]:
        return ["statistical", "ml"]

    def predict(self, draws, approach="all"):
        ...

    def predict_batch(self, draws, approach="all"):
        ...
```

Registre em `src/main.py` como novo comando.

## Adicionar nova abordagem

Crie em `src/strategies/<nome>/approaches/`:

```python
class MyApproach:
    def fit(self, draws):
        ...

    def predict_proba(self) -> np.ndarray:
        ...  # retorna array de 25 probabilidades

    @property
    def name(self) -> str:
        return "my_approach"
```

Registre no predictor da estratégia.
