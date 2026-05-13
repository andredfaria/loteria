# Task 3.5 — Mover `estrategias/` + renomear classes

**Onda:** 3 — Migrar infra
**Prioridade:** alta
**Tempo estimado:** ~25 min
**Depende de:** 3.4

## Objetivo

Mover `src/strategies/` para `src/lotofacil/infra/estrategias/`, renomeando subpastas e classes para PT. Deletar `src/strategies/base.py` (já tem equivalente Protocol em `dominio/estrategia.py`).

Atualizar `src/cli/app.py prever` para usar a estratégia movida — esta é a última peça da árvore órfã v2.0 ainda consumida pelo CLI.

## Descrição técnica

`src/strategies/` tem:
- `base.py` — `BaseStrategy` ABC (substituído por `EstrategiaBase` Protocol; deletar)
- `eleven_numbers/` — predictor com 4 abordagens (statistical, ml, neural, all)
- `quinze_numbers/` — 15 dezenas
- `future/twelve_numbers/`, `future/thirteen_numbers/`, `future/fourteen_numbers/` — placeholders ou parciais

## Arquivos envolvidos

**Mover:**

| De | Para |
|---|---|
| `src/strategies/eleven_numbers/` | `src/lotofacil/infra/estrategias/onze_dezenas/` |
| `src/strategies/quinze_numbers/` | `src/lotofacil/infra/estrategias/quinze_dezenas/` |
| `src/strategies/future/twelve_numbers/` | `src/lotofacil/infra/estrategias/doze_dezenas/` |
| `src/strategies/future/thirteen_numbers/` | `src/lotofacil/infra/estrategias/treze_dezenas/` |
| `src/strategies/future/fourteen_numbers/` | `src/lotofacil/infra/estrategias/quatorze_dezenas/` |

**Deletar:**
- `src/strategies/base.py` (substituído por `dominio/estrategia.py`)

**Renames de classes:**

| Antes | Depois |
|---|---|
| `ElevenNumbersStrategy` | `EstrategiaOnzeDezenas` |
| `QuinzeNumbersStrategy` (se existir) | `EstrategiaQuinzeDezenas` |
| (futuras) | `EstrategiaDozeDezenas`, `EstrategiaTrezeDezenas`, `EstrategiaQuatorzeDezenas` |
| `BaseStrategy` (em base.py) | (deletado — usar Protocol `EstrategiaBase`) |

**Renames de subarquivos dentro de cada estratégia:**

| Antes | Depois |
|---|---|
| `predictor.py` | `preditor.py` |
| `statistical.py` | `estatistico.py` |
| `ml.py` | `ml.py` (mantém) |
| `neural.py` | `neural.py` (mantém) |

**Modificar:**

- `src/cli/app.py` comando `prever` — substituir:
  ```python
  from data.loader import load_draws, load_draws_from_json
  from strategies.eleven_numbers.predictor import ElevenNumbersStrategy
  ```
  por:
  ```python
  from lotofacil.infra.dados.leitor import carregar_sorteios, carregar_sorteios_de_json
  from lotofacil.infra.estrategias.onze_dezenas.preditor import EstrategiaOnzeDezenas
  ```

## Dependências

- 3.4

## Critérios de aceite

- [ ] `from lotofacil.infra.estrategias.onze_dezenas.preditor import EstrategiaOnzeDezenas` funciona
- [ ] `EstrategiaOnzeDezenas` satisfaz `EstrategiaBase` Protocol (runtime-checkable)
- [ ] `grep -rn "from strategies\.\|from src.strategies" src/cli/ src/dashboard/` retorna 0
- [ ] `lotofacil prever` funciona
- [ ] `lotofacil prever --approach ml` funciona (ainda flag EN; renomeia na onda 5)
- [ ] `pytest` passa

## Passos detalhados

- [ ] **Passo 1:** Listar estrutura atual

```bash
find src/strategies -type f -name "*.py" | sort
```

- [ ] **Passo 2:** `git mv` das estratégias existentes

```bash
git mv src/strategies/eleven_numbers/ src/lotofacil/infra/estrategias/onze_dezenas/
git mv src/strategies/quinze_numbers/ src/lotofacil/infra/estrategias/quinze_dezenas/
git mv src/strategies/future/twelve_numbers/ src/lotofacil/infra/estrategias/doze_dezenas/ 2>/dev/null
git mv src/strategies/future/thirteen_numbers/ src/lotofacil/infra/estrategias/treze_dezenas/ 2>/dev/null
git mv src/strategies/future/fourteen_numbers/ src/lotofacil/infra/estrategias/quatorze_dezenas/ 2>/dev/null
```

- [ ] **Passo 3:** Deletar `base.py` e `future/` vazia

```bash
git rm src/strategies/base.py
git rm src/strategies/__init__.py
[ -d src/strategies/future ] && rmdir src/strategies/future 2>/dev/null
[ -d src/strategies ] && rmdir src/strategies 2>/dev/null
```

- [ ] **Passo 4:** Renomear `predictor.py` → `preditor.py` em cada estratégia

```bash
for dir in src/lotofacil/infra/estrategias/*/; do
  [ -f "${dir}predictor.py" ] && git mv "${dir}predictor.py" "${dir}preditor.py"
  [ -f "${dir}statistical.py" ] && git mv "${dir}statistical.py" "${dir}estatistico.py"
done
```

- [ ] **Passo 5:** Renomear classes nos arquivos movidos

```bash
sed -i \
  -e 's/class ElevenNumbersStrategy\b/class EstrategiaOnzeDezenas/g' \
  -e 's/\bElevenNumbersStrategy\b/EstrategiaOnzeDezenas/g' \
  -e 's/class QuinzeNumbersStrategy\b/class EstrategiaQuinzeDezenas/g' \
  -e 's/\bQuinzeNumbersStrategy\b/EstrategiaQuinzeDezenas/g' \
  src/lotofacil/infra/estrategias/*/*.py
```

E remover qualquer herança de `BaseStrategy` ABC; substituir pelo Protocol:

```bash
sed -i 's|from src\.strategies\.base import BaseStrategy||g' src/lotofacil/infra/estrategias/*/*.py
sed -i 's|from strategies\.base import BaseStrategy||g' src/lotofacil/infra/estrategias/*/*.py
sed -i 's|(BaseStrategy)||g' src/lotofacil/infra/estrategias/*/*.py
```

Adicionar import de `EstrategiaBase` se necessário para type hints (opcional).

- [ ] **Passo 6:** Atualizar imports internos das estratégias

```bash
sed -i \
  -e 's|from data\.loader|from lotofacil.infra.dados.leitor|g' \
  -e 's|from features\.|from lotofacil.infra.atributos.|g' \
  -e 's|from lotofacil_ml\.|from lotofacil.infra.|g' \
  -e 's|from core\.models|from lotofacil.dominio.entidades|g' \
  -e 's|\bDraw\b|Sorteio|g' \
  -e 's|\bPrediction\b|Predicao|g' \
  src/lotofacil/infra/estrategias/*/*.py
```

(`Draw`/`Prediction` ainda funcionam via alias; mas vamos usar nome final agora.)

- [ ] **Passo 7:** Reescrever `__init__.py` de cada estratégia

`src/lotofacil/infra/estrategias/__init__.py`:

```python
"""Estratégias de predição. Cada subpacote implementa EstrategiaBase."""
```

`src/lotofacil/infra/estrategias/onze_dezenas/__init__.py`:

```python
"""Estratégia que prevê 11 dezenas (de 25)."""
from .preditor import EstrategiaOnzeDezenas

__all__ = ["EstrategiaOnzeDezenas"]
```

(Repetir padrão para outras estratégias existentes.)

- [ ] **Passo 8:** Atualizar `src/cli/app.py` (comando `prever`)

Substituir:

```python
from data.loader import load_draws, load_draws_from_json
from strategies.eleven_numbers.predictor import ElevenNumbersStrategy
# ...
draws = load_draws(source="db")
# ...
strategy = ElevenNumbersStrategy()
pred = strategy.predict(draws, approach=approach)
```

Por:

```python
from lotofacil.infra.dados.leitor import carregar_sorteios, carregar_sorteios_de_json
from lotofacil.infra.estrategias.onze_dezenas import EstrategiaOnzeDezenas
# ...
draws = carregar_sorteios(source="db")
# ...
estrategia = EstrategiaOnzeDezenas()
pred = estrategia.predict(draws, abordagem=approach)
```

Atenção: parâmetro `approach=` ainda existe (renomeia para `abordagem=` na onda 5 task 04).

- [ ] **Passo 9:** Validar imports

```bash
python -c "from lotofacil.infra.estrategias.onze_dezenas import EstrategiaOnzeDezenas; print('OK')"
python -c "from cli.app import app; print('OK')"
```

- [ ] **Passo 10:** Verificar residuais

```bash
grep -rn "from strategies\.\|from src.strategies\|ElevenNumbersStrategy" src/cli/ src/dashboard/
# 0 esperado
```

- [ ] **Passo 11:** Testes

```bash
pytest
```

- [ ] **Passo 12:** Smoke

```bash
lotofacil prever
lotofacil prever --approach ml
```

Esperado: gera predição com 11 dezenas e salva em `saida/jogos/predicao_*.json`.

- [ ] **Passo 13:** Commit

```bash
git add -A
git commit -m "refactor(infra): move strategies → infra/estrategias (PT)

Subpastas e classes em PT:
- eleven_numbers/ → onze_dezenas/    (ElevenNumbersStrategy → EstrategiaOnzeDezenas)
- quinze_numbers/ → quinze_dezenas/  (QuinzeNumbersStrategy → EstrategiaQuinzeDezenas)
- future/twelve_numbers/ → doze_dezenas/
- future/thirteen_numbers/ → treze_dezenas/
- future/fourteen_numbers/ → quatorze_dezenas/
- predictor.py → preditor.py
- statistical.py → estatistico.py

src/strategies/base.py deletado (substituído por dominio/estrategia.py
Protocol).

cli/app.py prever atualizado. Última task da onda 3 — todas as infras
canônicas migradas."
```
