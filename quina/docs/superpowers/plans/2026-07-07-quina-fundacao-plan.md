# Quina — Fase 1 (Fundação) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up `quina/` as an independent sibling project (same convention as `super-sete/`, `dia-de-sorte/`) with the domain rules, SQLite persistence, Caixa API data collection, and a basic CLI (`quina dados atualizar` / `quina dados status`) needed before any statistics, ML, backtest, portfolio, or dashboard work can start.

**Architecture:** 4-layer package at `quina/src/quina/` mirroring `lotofacil/src/lotofacil/` (`dominio/` pure rules and entities, `infra/config.py` + `infra/dados/` for persistence and API access, `interface/cli/` Typer commands). No dependency on the `lotofacil` package — fully independent, per the approved design.

**Tech Stack:** Python 3.12 (>=3.11 required), Pydantic 2, Typer, Rich, `requests` + `tenacity` for retried HTTP, stdlib `sqlite3`. Dev: `pytest`, `responses` (HTTP mocking).

## Global Constraints

- Game rules (verified live against `https://loteriascaixa-api.herokuapp.com/api/quina/latest`): `TOTAL_NUMEROS = 80`, `NUMEROS_POR_SORTEIO = 5`, `FAIXAS_ACERTOS = [2, 3, 4, 5]`. No `TABELA_PREMIOS` in this phase — Quina prize values are variable/proportional, not fixed; that belongs to the Backtest/Portfolio phases.
- `quina/` is a fully independent project — its own `pyproject.toml`, venv, SQLite DB. No imports from or into the `lotofacil` package.
- `quina/dados/` is a symlink to `~/quina-dados/` and is **not git-tracked** (verified `lotofacil/dados` is an untracked symlink today — nothing inside it can be committed). Sample/fixture draws instead live at `quina/testes/fixtures/sample_draws/`, which **is** committed.
- Follow existing repo naming conventions: Portuguese identifiers (`Sorteio`, `dezenas`, `concurso`), 4-layer architecture (`dominio` has no I/O or framework deps; `infra` implements persistence/API; `interface` is the CLI).
- Every module that needs a path or constant imports it from `quina.infra.config` — never `os.getcwd()` or ad-hoc relative paths.
- Entry point: `quina` CLI (Typer), registered via `[project.scripts]` in `pyproject.toml`.

---

## Task 1: Project Scaffold

**Files:**
- Create: `quina/pyproject.toml`
- Create: `quina/.gitignore`
- Create: `quina/src/quina/__init__.py`
- Create: `quina/src/quina/dominio/__init__.py`
- Create: `quina/src/quina/infra/__init__.py`
- Create: `quina/src/quina/infra/dados/__init__.py`
- Create: `quina/src/quina/interface/__init__.py`
- Create: `quina/src/quina/interface/cli/__init__.py`
- Create: `quina/testes/fixtures/sample_draws/concurso_7035.json` … `concurso_7059.json` (25 real draws, fetched live from the Caixa API on 2026-07-07)

**Interfaces:**
- Produces: an installable `quina` package (`pip install -e ".[dev]"` works, `import quina` works), a venv at `quina/venv/`, 25 committed fixture files under `quina/testes/fixtures/sample_draws/` for later tasks to read, and a `dados/` symlink to `~/quina-dados/` for later tasks to read/write through.

- [ ] **Step 1: Create the directory tree and empty `__init__.py` files**

```bash
mkdir -p quina/src/quina/dominio
mkdir -p quina/src/quina/infra/dados
mkdir -p quina/src/quina/interface/cli
mkdir -p quina/testes/unidade
mkdir -p quina/testes/integracao
mkdir -p quina/testes/fixtures/sample_draws
mkdir -p quina/saida

touch quina/src/quina/__init__.py
touch quina/src/quina/dominio/__init__.py
touch quina/src/quina/infra/__init__.py
touch quina/src/quina/infra/dados/__init__.py
touch quina/src/quina/interface/__init__.py
touch quina/src/quina/interface/cli/__init__.py
```

- [ ] **Step 2: Create the `dados/` symlink**

```bash
mkdir -p ~/quina-dados
ln -s ~/quina-dados quina/dados
```

Expected: `ls -la quina/dados` shows it as a symlink pointing at `/home/andre/quina-dados`.

- [ ] **Step 3: Write `pyproject.toml`**

File: `quina/pyproject.toml`

```toml
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "quina-prediction"
version = "0.1.0"
description = "Sistema de coleta e analise de dados para a Quina"
requires-python = ">=3.11"
dependencies = [
    "requests>=2.31.0",
    "tenacity>=8.2.0",
    "pydantic>=2.0.0",
    "typer>=0.9.0",
    "rich>=13.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "responses>=0.23.0",
]

[project.scripts]
quina = "quina.interface.cli.app:app"

[tool.setuptools.packages.find]
where = ["src"]
include = ["quina*"]

[tool.pytest.ini_options]
testpaths = ["testes"]
```

- [ ] **Step 4: Write `.gitignore`**

File: `quina/.gitignore`

```
venv/
__pycache__/
*.pyc
*.egg-info/
.pytest_cache/
dados/
saida/
.env
```

- [ ] **Step 5: Fetch and write the 25 fixture draws**

These are real Quina draws (concursos 7035–7059), already fetched from the API on 2026-07-07. Write each as its own file under `quina/testes/fixtures/sample_draws/`, format matching the real API response shape (only the fields the code reads: `concurso`, `data`, `dezenas`).

```bash
cat > quina/testes/fixtures/sample_draws/concurso_7035.json <<'EOF'
{"concurso": 7035, "data": "26/05/2026", "dezenas": ["14", "15", "48", "58", "73"]}
EOF
cat > quina/testes/fixtures/sample_draws/concurso_7036.json <<'EOF'
{"concurso": 7036, "data": "27/05/2026", "dezenas": ["15", "42", "63", "66", "77"]}
EOF
cat > quina/testes/fixtures/sample_draws/concurso_7037.json <<'EOF'
{"concurso": 7037, "data": "28/05/2026", "dezenas": ["09", "26", "42", "55", "66"]}
EOF
cat > quina/testes/fixtures/sample_draws/concurso_7038.json <<'EOF'
{"concurso": 7038, "data": "29/05/2026", "dezenas": ["02", "31", "39", "64", "73"]}
EOF
cat > quina/testes/fixtures/sample_draws/concurso_7039.json <<'EOF'
{"concurso": 7039, "data": "30/05/2026", "dezenas": ["12", "15", "16", "67", "80"]}
EOF
cat > quina/testes/fixtures/sample_draws/concurso_7040.json <<'EOF'
{"concurso": 7040, "data": "01/06/2026", "dezenas": ["05", "23", "52", "56", "67"]}
EOF
cat > quina/testes/fixtures/sample_draws/concurso_7041.json <<'EOF'
{"concurso": 7041, "data": "02/06/2026", "dezenas": ["25", "28", "49", "56", "75"]}
EOF
cat > quina/testes/fixtures/sample_draws/concurso_7042.json <<'EOF'
{"concurso": 7042, "data": "03/06/2026", "dezenas": ["10", "13", "25", "36", "60"]}
EOF
cat > quina/testes/fixtures/sample_draws/concurso_7043.json <<'EOF'
{"concurso": 7043, "data": "05/06/2026", "dezenas": ["10", "20", "21", "29", "46"]}
EOF
cat > quina/testes/fixtures/sample_draws/concurso_7044.json <<'EOF'
{"concurso": 7044, "data": "06/06/2026", "dezenas": ["02", "05", "30", "54", "73"]}
EOF
cat > quina/testes/fixtures/sample_draws/concurso_7045.json <<'EOF'
{"concurso": 7045, "data": "08/06/2026", "dezenas": ["12", "13", "17", "54", "71"]}
EOF
cat > quina/testes/fixtures/sample_draws/concurso_7046.json <<'EOF'
{"concurso": 7046, "data": "09/06/2026", "dezenas": ["02", "12", "37", "68", "76"]}
EOF
cat > quina/testes/fixtures/sample_draws/concurso_7047.json <<'EOF'
{"concurso": 7047, "data": "10/06/2026", "dezenas": ["06", "11", "26", "50", "61"]}
EOF
cat > quina/testes/fixtures/sample_draws/concurso_7048.json <<'EOF'
{"concurso": 7048, "data": "11/06/2026", "dezenas": ["09", "25", "34", "56", "70"]}
EOF
cat > quina/testes/fixtures/sample_draws/concurso_7049.json <<'EOF'
{"concurso": 7049, "data": "12/06/2026", "dezenas": ["09", "14", "25", "44", "67"]}
EOF
cat > quina/testes/fixtures/sample_draws/concurso_7050.json <<'EOF'
{"concurso": 7050, "data": "14/06/2026", "dezenas": ["24", "36", "61", "66", "74"]}
EOF
cat > quina/testes/fixtures/sample_draws/concurso_7051.json <<'EOF'
{"concurso": 7051, "data": "28/06/2026", "dezenas": ["19", "32", "50", "73", "75"]}
EOF
cat > quina/testes/fixtures/sample_draws/concurso_7052.json <<'EOF'
{"concurso": 7052, "data": "29/06/2026", "dezenas": ["09", "55", "63", "65", "80"]}
EOF
cat > quina/testes/fixtures/sample_draws/concurso_7053.json <<'EOF'
{"concurso": 7053, "data": "30/06/2026", "dezenas": ["02", "15", "54", "63", "72"]}
EOF
cat > quina/testes/fixtures/sample_draws/concurso_7054.json <<'EOF'
{"concurso": 7054, "data": "01/07/2026", "dezenas": ["02", "11", "34", "63", "68"]}
EOF
cat > quina/testes/fixtures/sample_draws/concurso_7055.json <<'EOF'
{"concurso": 7055, "data": "02/07/2026", "dezenas": ["07", "20", "22", "38", "66"]}
EOF
cat > quina/testes/fixtures/sample_draws/concurso_7056.json <<'EOF'
{"concurso": 7056, "data": "03/07/2026", "dezenas": ["28", "41", "43", "50", "57"]}
EOF
cat > quina/testes/fixtures/sample_draws/concurso_7057.json <<'EOF'
{"concurso": 7057, "data": "04/07/2026", "dezenas": ["34", "38", "47", "63", "75"]}
EOF
cat > quina/testes/fixtures/sample_draws/concurso_7058.json <<'EOF'
{"concurso": 7058, "data": "06/07/2026", "dezenas": ["08", "26", "27", "66", "79"]}
EOF
cat > quina/testes/fixtures/sample_draws/concurso_7059.json <<'EOF'
{"concurso": 7059, "data": "07/07/2026", "dezenas": ["27", "47", "57", "70", "78"]}
EOF
```

Expected: `ls quina/testes/fixtures/sample_draws | wc -l` prints `25`.

- [ ] **Step 6: Create the venv and install the package**

```bash
cd quina
python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
python -c "import quina; print('ok')"
```

Expected: last line prints `ok`. If `pip install` fails because there's no code yet — it won't; an editable install only needs the package directories to exist with `__init__.py`, which Step 1 created.

- [ ] **Step 7: Commit**

```bash
cd "$(git rev-parse --show-toplevel)"
git add quina/pyproject.toml quina/.gitignore quina/src quina/testes/fixtures
git commit -m "$(cat <<'EOF'
chore(quina): scaffold quina project structure

New sibling project to lotofacil/, super-sete/, dia-de-sorte/. Empty
4-layer package skeleton, pyproject.toml, and 25 real Quina draws
(concursos 7035-7059) committed as test fixtures — dados/ itself is a
symlink and can't be git-tracked.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Domain Rules

**Files:**
- Create: `quina/src/quina/dominio/regras.py`
- Test: `quina/testes/unidade/test_regras.py`

**Interfaces:**
- Produces: `TOTAL_NUMEROS=80`, `NUMEROS_POR_SORTEIO=5`, `VALID_NUMBERS: set[int]`, `FAIXAS_ACERTOS=[2,3,4,5]`, `validar_dezenas(dezenas: list[int]) -> bool`, `contar_acertos(aposta: list[int], resultado: list[int]) -> int`, `contar_pares(dezenas: list[int]) -> int`, `contar_impares(dezenas: list[int]) -> int`, `soma_dezenas(dezenas: list[int]) -> int`, `repetidos_anterior(atual: list[int], anterior: list[int]) -> int`, `estatisticas_dezenas(dezenas: list[int]) -> dict`, `gerar_combinacoes(n: int) -> Iterator[tuple[int, ...]]`, `total_combinacoes(n: int = NUMEROS_POR_SORTEIO) -> int`.

- [ ] **Step 1: Write the failing test**

File: `quina/testes/unidade/test_regras.py`

```python
from quina.dominio.regras import (
    FAIXAS_ACERTOS,
    NUMEROS_POR_SORTEIO,
    TOTAL_NUMEROS,
    VALID_NUMBERS,
    contar_acertos,
    contar_impares,
    contar_pares,
    estatisticas_dezenas,
    gerar_combinacoes,
    repetidos_anterior,
    soma_dezenas,
    total_combinacoes,
    validar_dezenas,
)


class TestConstantes:
    def test_total_numeros(self):
        assert TOTAL_NUMEROS == 80

    def test_numeros_por_sorteio(self):
        assert NUMEROS_POR_SORTEIO == 5

    def test_valid_numbers_range(self):
        assert VALID_NUMBERS == set(range(1, 81))

    def test_faixas_acertos(self):
        assert FAIXAS_ACERTOS == [2, 3, 4, 5]


class TestValidarDezenas:
    def test_valid(self):
        assert validar_dezenas([1, 2, 3, 4, 5]) is True

    def test_invalid_count_too_few(self):
        assert validar_dezenas([1, 2, 3, 4]) is False

    def test_invalid_count_too_many(self):
        assert validar_dezenas([1, 2, 3, 4, 5, 6]) is False

    def test_invalid_duplicates(self):
        assert validar_dezenas([1, 1, 2, 3, 4]) is False

    def test_invalid_out_of_range(self):
        assert validar_dezenas([1, 2, 3, 4, 81]) is False
        assert validar_dezenas([0, 2, 3, 4, 5]) is False


class TestContarAcertos:
    def test_full_match(self):
        assert contar_acertos([14, 15, 48, 58, 73], [14, 15, 48, 58, 73]) == 5

    def test_partial_match(self):
        assert contar_acertos([14, 15, 48, 58, 73], [14, 15, 1, 2, 3]) == 2

    def test_no_match(self):
        assert contar_acertos([1, 2, 3, 4, 5], [6, 7, 8, 9, 10]) == 0


class TestEstatisticas:
    def test_contar_pares_impares(self):
        assert contar_pares([14, 15, 48, 58, 73]) == 3
        assert contar_impares([14, 15, 48, 58, 73]) == 2

    def test_soma_dezenas(self):
        assert soma_dezenas([14, 15, 48, 58, 73]) == 208

    def test_repetidos_anterior(self):
        assert repetidos_anterior([14, 15, 48, 58, 73], [15, 42, 63, 66, 77]) == 1

    def test_estatisticas_dezenas(self):
        stats = estatisticas_dezenas([14, 15, 48, 58, 73])
        assert stats == {"pares": 3, "impares": 2, "soma": 208}


class TestCombinacoes:
    def test_total_combinacoes_default(self):
        assert total_combinacoes() == 24040016

    def test_gerar_combinacoes_count(self):
        combos = list(gerar_combinacoes(2))
        assert len(combos) == 3160
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd quina && source venv/bin/activate && pytest testes/unidade/test_regras.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'quina.dominio.regras'`

- [ ] **Step 3: Write the implementation**

File: `quina/src/quina/dominio/regras.py`

```python
from __future__ import annotations

import itertools
from math import comb
from typing import Iterator

TOTAL_NUMEROS = 80
NUMEROS_POR_SORTEIO = 5
VALID_NUMBERS = set(range(1, TOTAL_NUMEROS + 1))

FAIXAS_ACERTOS = [2, 3, 4, 5]


def validar_dezenas(dezenas: list[int]) -> bool:
    if len(dezenas) != NUMEROS_POR_SORTEIO:
        return False
    if len(set(dezenas)) != NUMEROS_POR_SORTEIO:
        return False
    return all(d in VALID_NUMBERS for d in dezenas)


def contar_acertos(aposta: list[int], resultado: list[int]) -> int:
    return len(set(aposta) & set(resultado))


def contar_pares(dezenas: list[int]) -> int:
    return sum(1 for d in dezenas if d % 2 == 0)


def contar_impares(dezenas: list[int]) -> int:
    return NUMEROS_POR_SORTEIO - contar_pares(dezenas)


def soma_dezenas(dezenas: list[int]) -> int:
    return sum(dezenas)


def repetidos_anterior(atual: list[int], anterior: list[int]) -> int:
    return len(set(atual) & set(anterior))


def estatisticas_dezenas(dezenas: list[int]) -> dict:
    return {
        "pares": contar_pares(dezenas),
        "impares": contar_impares(dezenas),
        "soma": soma_dezenas(dezenas),
    }


def gerar_combinacoes(n: int) -> Iterator[tuple[int, ...]]:
    yield from itertools.combinations(VALID_NUMBERS, n)


def total_combinacoes(n: int = NUMEROS_POR_SORTEIO) -> int:
    return comb(TOTAL_NUMEROS, n)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd quina && source venv/bin/activate && pytest testes/unidade/test_regras.py -v`
Expected: PASS — all 18 tests green.

- [ ] **Step 5: Commit**

```bash
cd "$(git rev-parse --show-toplevel)"
git add quina/src/quina/dominio/regras.py quina/testes/unidade/test_regras.py
git commit -m "$(cat <<'EOF'
feat(quina): add domain rules (regras.py)

TOTAL_NUMEROS=80, NUMEROS_POR_SORTEIO=5, FAIXAS_ACERTOS=[2,3,4,5] —
verified live against the Caixa API. Pure validation/statistics
functions ported from lotofacil.dominio.regras.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Domain Entities and Exceptions

**Files:**
- Create: `quina/src/quina/dominio/entidades.py`
- Create: `quina/src/quina/dominio/excecoes.py`
- Test: `quina/testes/unidade/test_entidades.py`

**Interfaces:**
- Consumes: `NUMEROS_POR_SORTEIO`, `TOTAL_NUMEROS` from `quina.dominio.regras` (Task 2).
- Produces: `Sorteio` (Pydantic `BaseModel`: `concurso: int`, `data: str`, `dezenas: list[int]`, validated/sorted), `SorteioBruto` (Pydantic: `concurso: int`, `data: str`, `dezenas: list[str]`, `dezenasOrdemSorteio: Optional[list[str]]`), `Draw = Sorteio` alias. `QuinaError`, `SorteioNaoEncontrado(QuinaError)`, `BaseDesatualizada(QuinaError)`.

- [ ] **Step 1: Write the failing test**

File: `quina/testes/unidade/test_entidades.py`

```python
import pytest
from pydantic import ValidationError

from quina.dominio.entidades import Sorteio, SorteioBruto
from quina.dominio.excecoes import BaseDesatualizada, QuinaError, SorteioNaoEncontrado


class TestSorteio:
    def test_valid(self):
        s = Sorteio(concurso=7059, data="07/07/2026", dezenas=[27, 47, 57, 70, 78])
        assert s.concurso == 7059
        assert len(s.dezenas) == 5

    def test_dezenas_sorted(self):
        s = Sorteio(concurso=7059, data="07/07/2026", dezenas=[78, 27, 70, 47, 57])
        assert s.dezenas == [27, 47, 57, 70, 78]

    def test_invalid_too_few(self):
        with pytest.raises(ValidationError):
            Sorteio(concurso=1, data="01/01/2026", dezenas=[1, 2, 3, 4])

    def test_invalid_too_many(self):
        with pytest.raises(ValidationError):
            Sorteio(concurso=1, data="01/01/2026", dezenas=[1, 2, 3, 4, 5, 6])

    def test_invalid_duplicates(self):
        with pytest.raises(ValidationError):
            Sorteio(concurso=1, data="01/01/2026", dezenas=[1, 1, 2, 3, 4])

    def test_invalid_out_of_range(self):
        with pytest.raises(ValidationError):
            Sorteio(concurso=1, data="01/01/2026", dezenas=[1, 2, 3, 4, 81])


class TestSorteioBruto:
    def test_valid(self):
        sb = SorteioBruto(
            concurso=7059,
            data="07/07/2026",
            dezenas=["27", "47", "57", "70", "78"],
            dezenasOrdemSorteio=["57", "78", "27", "70", "47"],
        )
        assert sb.concurso == 7059
        assert sb.dezenas == ["27", "47", "57", "70", "78"]


class TestExcecoes:
    def test_hierarchy(self):
        assert issubclass(SorteioNaoEncontrado, QuinaError)
        assert issubclass(BaseDesatualizada, QuinaError)
        assert issubclass(QuinaError, Exception)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd quina && source venv/bin/activate && pytest testes/unidade/test_entidades.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'quina.dominio.entidades'`

- [ ] **Step 3: Write the implementation**

File: `quina/src/quina/dominio/excecoes.py`

```python
class QuinaError(Exception): ...
class SorteioNaoEncontrado(QuinaError): ...
class BaseDesatualizada(QuinaError): ...
```

File: `quina/src/quina/dominio/entidades.py`

```python
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator

from quina.dominio.regras import NUMEROS_POR_SORTEIO, TOTAL_NUMEROS


class Sorteio(BaseModel):
    concurso: int = Field(..., ge=1)
    data: str
    dezenas: list[int]

    @field_validator("dezenas", mode="after")
    @classmethod
    def validar_dezenas(cls, v: list[int]) -> list[int]:
        if len(v) != NUMEROS_POR_SORTEIO:
            raise ValueError(f"Esperado {NUMEROS_POR_SORTEIO} dezenas, obtido {len(v)}")
        if len(set(v)) != NUMEROS_POR_SORTEIO:
            raise ValueError("Dezenas devem ser unicas")
        if not all(1 <= d <= TOTAL_NUMEROS for d in v):
            raise ValueError(f"Dezenas devem estar entre 1-{TOTAL_NUMEROS}")
        return sorted(v)


class SorteioBruto(BaseModel):
    concurso: int
    data: str
    dezenas: list[str]
    dezenasOrdemSorteio: Optional[list[str]] = None


Draw = Sorteio
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd quina && source venv/bin/activate && pytest testes/unidade/test_entidades.py -v`
Expected: PASS — all 8 tests green.

- [ ] **Step 5: Commit**

```bash
cd "$(git rev-parse --show-toplevel)"
git add quina/src/quina/dominio/entidades.py quina/src/quina/dominio/excecoes.py quina/testes/unidade/test_entidades.py
git commit -m "$(cat <<'EOF'
feat(quina): add domain entities (Sorteio, SorteioBruto) and exceptions

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Infra Config

**Files:**
- Create: `quina/src/quina/infra/config.py`
- Test: `quina/testes/unidade/test_config.py`

**Interfaces:**
- Consumes: `quina.dominio.regras` constants (Task 2), for the cross-check test only.
- Produces: `PROJETO_RAIZ`, `DADOS_DIR`, `SAIDA_DIR`, `DB_PATH` (all `pathlib.Path`), `TOTAL_NUMEROS=80`, `NUMEROS_POR_SORTEIO=5`, `VALID_NUMBERS`, `FAIXAS_ACERTOS=[2,3,4,5]`, `API_BASE_URL`, `API_QUINA`, `API_TIMEOUT=30`, `API_RETRIES=5`, `API_RETRY_MIN=1`, `API_RETRY_MAX=10`, `USER_AGENT`.

- [ ] **Step 1: Write the failing test**

File: `quina/testes/unidade/test_config.py`

```python
from quina.dominio.regras import FAIXAS_ACERTOS as REGRAS_FAIXAS
from quina.dominio.regras import NUMEROS_POR_SORTEIO as REGRAS_NPS
from quina.dominio.regras import TOTAL_NUMEROS as REGRAS_TOTAL
from quina.infra.config import (
    API_QUINA,
    DADOS_DIR,
    DB_PATH,
    FAIXAS_ACERTOS,
    NUMEROS_POR_SORTEIO,
    SAIDA_DIR,
    TOTAL_NUMEROS,
)


def test_game_constants_match_domain_rules():
    assert TOTAL_NUMEROS == REGRAS_TOTAL == 80
    assert NUMEROS_POR_SORTEIO == REGRAS_NPS == 5
    assert FAIXAS_ACERTOS == REGRAS_FAIXAS == [2, 3, 4, 5]


def test_api_endpoint():
    assert API_QUINA == "https://loteriascaixa-api.herokuapp.com/api/quina"


def test_dirs_exist():
    assert DADOS_DIR.exists()
    assert SAIDA_DIR.exists()
    assert DB_PATH.name == "quina.db"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd quina && source venv/bin/activate && pytest testes/unidade/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'quina.infra.config'`

- [ ] **Step 3: Write the implementation**

File: `quina/src/quina/infra/config.py`

```python
"""Paths, game rules, and API config for the Quina project."""
from pathlib import Path

PROJETO_RAIZ = Path(__file__).resolve().parent.parent.parent.parent
DADOS_DIR = PROJETO_RAIZ / "dados"
SAIDA_DIR = PROJETO_RAIZ / "saida"
DB_PATH = DADOS_DIR / "quina.db"

DADOS_DIR.mkdir(parents=True, exist_ok=True)
SAIDA_DIR.mkdir(parents=True, exist_ok=True)

TOTAL_NUMEROS = 80
NUMEROS_POR_SORTEIO = 5
VALID_NUMBERS = set(range(1, TOTAL_NUMEROS + 1))
FAIXAS_ACERTOS = [2, 3, 4, 5]

API_BASE_URL = "https://loteriascaixa-api.herokuapp.com/api"
API_QUINA = f"{API_BASE_URL}/quina"
API_TIMEOUT = 30
API_RETRIES = 5
API_RETRY_MIN = 1
API_RETRY_MAX = 10
USER_AGENT = "quina-prediction/0.1"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd quina && source venv/bin/activate && pytest testes/unidade/test_config.py -v`
Expected: PASS — all 3 tests green. (`DADOS_DIR.exists()` passes because it resolves through the symlink created in Task 1 Step 2.)

- [ ] **Step 5: Commit**

```bash
cd "$(git rev-parse --show-toplevel)"
git add quina/src/quina/infra/config.py quina/testes/unidade/test_config.py
git commit -m "$(cat <<'EOF'
feat(quina): add infra config (paths, game rules, API settings)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Database Layer

**Files:**
- Create: `quina/src/quina/infra/dados/banco.py`
- Test: `quina/testes/integracao/test_banco.py`

**Interfaces:**
- Consumes: `DB_PATH` from `quina.infra.config` (Task 4) as the default constructor argument.
- Produces: `DatabaseManager(db_path: Path = DB_PATH)` with methods `upsert_concurso(concurso: int, data: str, dezenas: list[int], raw: dict = None) -> None`, `count_concursos() -> int`, `get_all_concursos() -> list[dict]` (each `{"concurso": int, "data": str, "dezenas": list[int]}`, ordered ascending), `get_latest_concurso() -> Optional[dict]` (same shape, highest `concurso`, or `None` if empty). SQLite tables: `concursos` (used) and `predicoes` (schema only, unused until the ML phase).

- [ ] **Step 1: Write the failing test**

File: `quina/testes/integracao/test_banco.py`

```python
import json
import sqlite3

import pytest

from quina.infra.dados.banco import DatabaseManager


@pytest.fixture
def db(tmp_path):
    return DatabaseManager(db_path=tmp_path / "test_quina.db")


class TestDatabaseManager:
    def test_empty_db(self, db):
        assert db.count_concursos() == 0
        assert db.get_latest_concurso() is None
        assert db.get_all_concursos() == []

    def test_upsert_and_count(self, db):
        db.upsert_concurso(7059, "07/07/2026", [27, 47, 57, 70, 78])
        assert db.count_concursos() == 1

    def test_upsert_sorts_dezenas(self, db):
        db.upsert_concurso(7059, "07/07/2026", [78, 27, 70, 47, 57])
        latest = db.get_latest_concurso()
        assert latest["dezenas"] == [27, 47, 57, 70, 78]

    def test_upsert_is_idempotent(self, db):
        db.upsert_concurso(7059, "07/07/2026", [27, 47, 57, 70, 78])
        db.upsert_concurso(7059, "07/07/2026", [27, 47, 57, 70, 78])
        assert db.count_concursos() == 1

    def test_upsert_updates_existing(self, db):
        db.upsert_concurso(7059, "07/07/2026", [1, 2, 3, 4, 5])
        db.upsert_concurso(7059, "07/07/2026", [27, 47, 57, 70, 78])
        latest = db.get_latest_concurso()
        assert latest["dezenas"] == [27, 47, 57, 70, 78]

    def test_get_latest_concurso(self, db):
        db.upsert_concurso(7058, "06/07/2026", [8, 26, 27, 66, 79])
        db.upsert_concurso(7059, "07/07/2026", [27, 47, 57, 70, 78])
        latest = db.get_latest_concurso()
        assert latest["concurso"] == 7059

    def test_get_all_concursos_ordered(self, db):
        db.upsert_concurso(7059, "07/07/2026", [27, 47, 57, 70, 78])
        db.upsert_concurso(7035, "26/05/2026", [14, 15, 48, 58, 73])
        all_c = db.get_all_concursos()
        assert [c["concurso"] for c in all_c] == [7035, 7059]

    def test_raw_json_persisted(self, tmp_path):
        db_path = tmp_path / "test_raw.db"
        db = DatabaseManager(db_path=db_path)
        db.upsert_concurso(7059, "07/07/2026", [27, 47, 57, 70, 78], raw={"loteria": "quina"})
        conn = sqlite3.connect(db_path)
        row = conn.execute("SELECT raw_json FROM concursos WHERE concurso=7059").fetchone()
        conn.close()
        assert json.loads(row[0]) == {"loteria": "quina"}

    def test_predicoes_table_exists(self, db):
        conn = sqlite3.connect(db.db_path)
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='predicoes'"
        ).fetchone()
        conn.close()
        assert row is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd quina && source venv/bin/activate && pytest testes/integracao/test_banco.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'quina.infra.dados.banco'`

- [ ] **Step 3: Write the implementation**

File: `quina/src/quina/infra/dados/banco.py`

```python
"""SQLite persistence layer for Quina data."""

import json
import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import List, Optional

from quina.infra.config import DB_PATH

logger = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self):
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS concursos (
                    concurso     INTEGER PRIMARY KEY,
                    data         TEXT NOT NULL,
                    dezenas      TEXT NOT NULL,
                    raw_json     TEXT
                );

                CREATE TABLE IF NOT EXISTS predicoes (
                    id                INTEGER PRIMARY KEY AUTOINCREMENT,
                    concurso_alvo     INTEGER NOT NULL,
                    dezenas_sugeridas TEXT NOT NULL,
                    probabilidades    TEXT NOT NULL,
                    confianca_media   REAL,
                    modelos_utilizados TEXT,
                    criado_em         TEXT DEFAULT (datetime('now')),
                    acertos           INTEGER,
                    validado_em       TEXT,
                    UNIQUE(concurso_alvo)
                );
            """)
        logger.debug("Database initialised at %s", self.db_path)

    # -- Concursos --------------------------------------------------------------

    def upsert_concurso(self, concurso: int, data: str, dezenas: List[int], raw: dict = None):
        dezenas_json = json.dumps(sorted(dezenas))
        raw_json = json.dumps(raw) if raw else None
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO concursos (concurso, data, dezenas, raw_json)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(concurso) DO UPDATE SET
                       data=excluded.data,
                       dezenas=excluded.dezenas,
                       raw_json=excluded.raw_json""",
                (concurso, data, dezenas_json, raw_json),
            )

    def count_concursos(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) FROM concursos").fetchone()
        return row[0] if row else 0

    def get_all_concursos(self) -> List[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT concurso, data, dezenas FROM concursos ORDER BY concurso"
            ).fetchall()
        return [
            {
                "concurso": r["concurso"],
                "data": r["data"],
                "dezenas": json.loads(r["dezenas"]),
            }
            for r in rows
        ]

    def get_latest_concurso(self) -> Optional[dict]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT concurso, data, dezenas FROM concursos ORDER BY concurso DESC LIMIT 1"
            ).fetchone()
        if row is None:
            return None
        return {
            "concurso": row["concurso"],
            "data": row["data"],
            "dezenas": json.loads(row["dezenas"]),
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd quina && source venv/bin/activate && pytest testes/integracao/test_banco.py -v`
Expected: PASS — all 9 tests green.

- [ ] **Step 5: Commit**

```bash
cd "$(git rev-parse --show-toplevel)"
git add quina/src/quina/infra/dados/banco.py quina/testes/integracao/test_banco.py
git commit -m "$(cat <<'EOF'
feat(quina): add SQLite persistence layer (DatabaseManager)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Local File Reader

**Files:**
- Create: `quina/src/quina/infra/dados/leitor.py`
- Test: `quina/testes/unidade/test_leitor.py`

**Interfaces:**
- Consumes: `NUMEROS_POR_SORTEIO`, `TOTAL_NUMEROS` from `quina.dominio.regras` (Task 2); reads the 25 fixture files from Task 1 (`quina/testes/fixtures/sample_draws/`).
- Produces: `Draw` (dataclass: `concurso: int`, `data: str`, `dezenas: List[int]`), `load_draws(dados_dir: str | Path) -> List[Draw]` — sorted ascending by `concurso`, silently skips malformed/invalid files.

- [ ] **Step 1: Write the failing test**

File: `quina/testes/unidade/test_leitor.py`

```python
from pathlib import Path

from quina.infra.dados.leitor import load_draws

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "sample_draws"


class TestLoadDrawsFixtures:
    def test_loads_all_25_fixtures(self):
        draws = load_draws(FIXTURES_DIR)
        assert len(draws) == 25

    def test_sorted_by_concurso(self):
        draws = load_draws(FIXTURES_DIR)
        concursos = [d.concurso for d in draws]
        assert concursos == sorted(concursos)
        assert concursos[0] == 7035
        assert concursos[-1] == 7059

    def test_dezenas_are_sorted_ints(self):
        draws = load_draws(FIXTURES_DIR)
        last = draws[-1]
        assert last.dezenas == [27, 47, 57, 70, 78]


class TestLoadDrawsEdgeCases:
    def test_empty_dir(self, tmp_path):
        assert load_draws(tmp_path) == []

    def test_skips_invalid_count(self, tmp_path):
        (tmp_path / "concurso_1.json").write_text(
            '{"concurso": 1, "data": "01/01/2026", "dezenas": ["1", "2", "3"]}'
        )
        assert load_draws(tmp_path) == []

    def test_skips_duplicates(self, tmp_path):
        (tmp_path / "concurso_1.json").write_text(
            '{"concurso": 1, "data": "01/01/2026", "dezenas": ["1", "1", "2", "3", "4"]}'
        )
        assert load_draws(tmp_path) == []

    def test_skips_out_of_range(self, tmp_path):
        (tmp_path / "concurso_1.json").write_text(
            '{"concurso": 1, "data": "01/01/2026", "dezenas": ["1", "2", "3", "4", "81"]}'
        )
        assert load_draws(tmp_path) == []

    def test_skips_malformed_json(self, tmp_path):
        (tmp_path / "concurso_1.json").write_text("not json")
        assert load_draws(tmp_path) == []

    def test_valid_and_invalid_mixed(self, tmp_path):
        (tmp_path / "concurso_1.json").write_text(
            '{"concurso": 1, "data": "01/01/2026", "dezenas": ["1", "2", "3", "4", "5"]}'
        )
        (tmp_path / "concurso_2.json").write_text(
            '{"concurso": 2, "data": "02/01/2026", "dezenas": ["1", "2", "3"]}'
        )
        draws = load_draws(tmp_path)
        assert len(draws) == 1
        assert draws[0].concurso == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd quina && source venv/bin/activate && pytest testes/unidade/test_leitor.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'quina.infra.dados.leitor'`

- [ ] **Step 3: Write the implementation**

File: `quina/src/quina/infra/dados/leitor.py`

```python
"""Load Quina draw history from local JSON files."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Union

from quina.dominio.regras import NUMEROS_POR_SORTEIO, TOTAL_NUMEROS

logger = logging.getLogger(__name__)


@dataclass
class Draw:
    concurso: int
    data: str
    dezenas: List[int]  # sorted ints, range 1-80


def load_draws(dados_dir: Union[str, Path]) -> List[Draw]:
    """
    Load all concurso_N.json files from dados_dir.

    Returns draws sorted by concurso number.
    Silently skips files with JSON errors or invalid data.
    """
    dados_path = Path(dados_dir)
    draws: List[Draw] = []

    for arquivo in dados_path.glob("concurso_*.json"):
        try:
            raw = json.loads(arquivo.read_text(encoding="utf-8"))
            dezenas = sorted(int(d) for d in raw["dezenas"])
            if len(dezenas) != NUMEROS_POR_SORTEIO:
                logger.warning(
                    "Skipping %s: expected %d dezenas, got %d",
                    arquivo.name, NUMEROS_POR_SORTEIO, len(dezenas),
                )
                continue
            if len(set(dezenas)) != NUMEROS_POR_SORTEIO:
                logger.warning("Skipping %s: dezenas contains duplicates", arquivo.name)
                continue
            if not all(1 <= d <= TOTAL_NUMEROS for d in dezenas):
                logger.warning(
                    "Skipping %s: dezenas out of range 1-%d", arquivo.name, TOTAL_NUMEROS
                )
                continue
            draws.append(Draw(
                concurso=int(raw["concurso"]),
                data=raw.get("data", ""),
                dezenas=dezenas,
            ))
        except Exception as exc:
            logger.warning("Skipping %s: %s", arquivo.name, exc)
            continue

    draws.sort(key=lambda d: d.concurso)
    return draws
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd quina && source venv/bin/activate && pytest testes/unidade/test_leitor.py -v`
Expected: PASS — all 9 tests green.

- [ ] **Step 5: Commit**

```bash
cd "$(git rev-parse --show-toplevel)"
git add quina/src/quina/infra/dados/leitor.py quina/testes/unidade/test_leitor.py
git commit -m "$(cat <<'EOF'
feat(quina): add local draw file reader (load_draws)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: Caixa API Fetcher

**Files:**
- Create: `quina/src/quina/infra/dados/api_caixa.py`
- Test: `quina/testes/integracao/test_api_caixa.py`

**Interfaces:**
- Consumes: `API_QUINA`, `API_TIMEOUT`, `API_RETRIES`, `API_RETRY_MIN`, `API_RETRY_MAX`, `DADOS_DIR`, `NUMEROS_POR_SORTEIO`, `TOTAL_NUMEROS`, `USER_AGENT` from `quina.infra.config` (Task 4); `DatabaseManager` from `quina.infra.dados.banco` (Task 5).
- Produces: `QuinaFetcher(db: Optional[DatabaseManager] = None, data_dir: Path = DADOS_DIR)` with `fetch_all_results() -> List[dict]`, `fetch_latest() -> Optional[dict]`, `fetch_by_concurso(numero: int) -> Optional[dict]`, `sync_new_draws() -> int`. Internal helper `_parse_record(raw: dict) -> Optional[dict]` (module-level, also unit-tested directly).

**Behavior note:** `sync_new_draws()` bootstraps an empty DB from local JSON files (via `fetch_all_results()`) before checking the API for new draws — this is a deliberate fix versus the equivalent `lotofacil` code, where `sync_new_draws()` returns `0` and never populates the DB on a first run with an empty `latest_local`.

- [ ] **Step 1: Write the failing test**

File: `quina/testes/integracao/test_api_caixa.py`

```python
import json
from functools import partial

import responses

from quina.infra.config import API_QUINA
from quina.infra.dados.api_caixa import QuinaFetcher, _parse_record
from quina.infra.dados.banco import DatabaseManager

RAW_7059 = {"concurso": 7059, "data": "07/07/2026", "dezenas": ["27", "47", "57", "70", "78"]}
RAW_7058 = {"concurso": 7058, "data": "06/07/2026", "dezenas": ["08", "26", "27", "66", "79"]}


class TestParseRecord:
    def test_valid(self):
        rec = _parse_record(RAW_7059)
        assert rec["concurso"] == 7059
        assert rec["dezenas"] == [27, 47, 57, 70, 78]

    def test_invalid_count(self):
        bad = {"concurso": 1, "data": "01/01/2026", "dezenas": ["1", "2", "3"]}
        assert _parse_record(bad) is None

    def test_invalid_range(self):
        bad = {"concurso": 1, "data": "01/01/2026", "dezenas": ["1", "2", "3", "4", "81"]}
        assert _parse_record(bad) is None

    def test_missing_field(self):
        assert _parse_record({"concurso": 1}) is None


class TestQuinaFetcher:
    @responses.activate
    def test_fetch_latest(self, tmp_path):
        responses.add(responses.GET, f"{API_QUINA}/latest", json=RAW_7059, status=200)
        db = DatabaseManager(db_path=tmp_path / "test.db")
        fetcher = QuinaFetcher(db=db, data_dir=tmp_path)

        result = fetcher.fetch_latest()

        assert result["concurso"] == 7059
        assert result["dezenas"] == [27, 47, 57, 70, 78]
        assert db.count_concursos() == 1
        assert (tmp_path / "concurso_7059.json").exists()

    @responses.activate
    def test_fetch_by_concurso_from_api(self, tmp_path):
        responses.add(responses.GET, f"{API_QUINA}/7059", json=RAW_7059, status=200)
        db = DatabaseManager(db_path=tmp_path / "test.db")
        fetcher = QuinaFetcher(db=db, data_dir=tmp_path)

        result = fetcher.fetch_by_concurso(7059)

        assert result["concurso"] == 7059
        assert db.count_concursos() == 1

    @responses.activate
    def test_fetch_by_concurso_from_db_skips_api(self, tmp_path):
        db = DatabaseManager(db_path=tmp_path / "test.db")
        db.upsert_concurso(7059, "07/07/2026", [27, 47, 57, 70, 78])
        fetcher = QuinaFetcher(db=db, data_dir=tmp_path)

        result = fetcher.fetch_by_concurso(7059)

        assert result["concurso"] == 7059
        assert len(responses.calls) == 0

    @responses.activate
    def test_sync_new_draws_bootstraps_empty_db_from_local_files(self, tmp_path):
        (tmp_path / "concurso_7058.json").write_text(json.dumps(RAW_7058))
        responses.add(responses.GET, f"{API_QUINA}/latest", json=RAW_7058, status=200)
        db = DatabaseManager(db_path=tmp_path / "test.db")
        fetcher = QuinaFetcher(db=db, data_dir=tmp_path)

        new_count = fetcher.sync_new_draws()

        assert db.count_concursos() == 1
        assert new_count == 0

    @responses.activate
    def test_sync_new_draws_fetches_gap(self, tmp_path):
        db = DatabaseManager(db_path=tmp_path / "test.db")
        db.upsert_concurso(7058, "06/07/2026", [8, 26, 27, 66, 79])
        responses.add(responses.GET, f"{API_QUINA}/latest", json=RAW_7059, status=200)
        responses.add(responses.GET, f"{API_QUINA}/7059", json=RAW_7059, status=200)
        fetcher = QuinaFetcher(db=db, data_dir=tmp_path)

        new_count = fetcher.sync_new_draws()

        assert new_count == 1
        assert db.count_concursos() == 2
        assert db.get_latest_concurso()["concurso"] == 7059

    @responses.activate
    def test_sync_new_draws_no_op_when_up_to_date(self, tmp_path):
        db = DatabaseManager(db_path=tmp_path / "test.db")
        db.upsert_concurso(7059, "07/07/2026", [27, 47, 57, 70, 78])
        responses.add(responses.GET, f"{API_QUINA}/latest", json=RAW_7059, status=200)
        fetcher = QuinaFetcher(db=db, data_dir=tmp_path)

        new_count = fetcher.sync_new_draws()

        assert new_count == 0
        assert db.count_concursos() == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd quina && source venv/bin/activate && pytest testes/integracao/test_api_caixa.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'quina.infra.dados.api_caixa'`

- [ ] **Step 3: Write the implementation**

File: `quina/src/quina/infra/dados/api_caixa.py`

```python
"""Data fetcher: loads from local dados/ files and syncs with the Caixa API."""

import json
import logging
from pathlib import Path
from typing import List, Optional

import requests
from tenacity import before_sleep_log, retry, stop_after_attempt, wait_exponential

from quina.infra.config import (
    API_QUINA,
    API_RETRIES,
    API_RETRY_MAX,
    API_RETRY_MIN,
    API_TIMEOUT,
    DADOS_DIR,
    NUMEROS_POR_SORTEIO,
    TOTAL_NUMEROS,
    USER_AGENT,
)
from quina.infra.dados.banco import DatabaseManager

logger = logging.getLogger(__name__)


def _parse_record(raw: dict) -> Optional[dict]:
    """Validate and normalize a raw draw dict. Returns None if invalid."""
    try:
        concurso = int(raw["concurso"])
        data = str(raw.get("data", ""))
        dezenas = [int(d) for d in raw["dezenas"]]
        if len(dezenas) != NUMEROS_POR_SORTEIO:
            logger.warning(
                "Concurso %d: expected %d dezenas, got %d", concurso, NUMEROS_POR_SORTEIO, len(dezenas)
            )
            return None
        if not all(1 <= d <= TOTAL_NUMEROS for d in dezenas):
            logger.warning("Concurso %d: dezenas out of range 1-%d", concurso, TOTAL_NUMEROS)
            return None
        return {"concurso": concurso, "data": data, "dezenas": dezenas, "raw": raw}
    except (KeyError, ValueError, TypeError) as exc:
        logger.debug("Skipping invalid record: %s", exc)
        return None


class QuinaFetcher:
    def __init__(self, db: Optional[DatabaseManager] = None, data_dir: Path = DADOS_DIR):
        self.db = db or DatabaseManager()
        self.data_dir = data_dir
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": USER_AGENT})

    # -- Local file loading -------------------------------------------------

    def _load_local_files(self) -> List[dict]:
        records = []
        files = sorted(self.data_dir.glob("concurso_*.json"))
        logger.info("Loading %d local JSON files from %s", len(files), self.data_dir)
        for f in files:
            try:
                with open(f, encoding="utf-8") as fh:
                    raw = json.load(fh)
                rec = _parse_record(raw)
                if rec:
                    records.append(rec)
            except Exception as exc:
                logger.debug("Skipping %s: %s", f.name, exc)
        logger.info("Loaded %d valid concursos from local files", len(records))
        return records

    # -- API ------------------------------------------------------------------

    @retry(
        stop=stop_after_attempt(API_RETRIES),
        wait=wait_exponential(multiplier=1, min=API_RETRY_MIN, max=API_RETRY_MAX),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    def _get_api(self, url: str) -> dict:
        resp = self._session.get(url, timeout=API_TIMEOUT)
        resp.raise_for_status()
        return resp.json()

    def _fetch_concurso_api(self, numero: int) -> Optional[dict]:
        try:
            raw = self._get_api(f"{API_QUINA}/{numero}")
            return _parse_record(raw)
        except Exception as exc:
            logger.warning("API fetch failed for concurso %d: %s", numero, exc)
            return None

    def _fetch_latest_api(self) -> Optional[dict]:
        try:
            raw = self._get_api(f"{API_QUINA}/latest")
            return _parse_record(raw)
        except Exception as exc:
            logger.warning("API fetch_latest failed: %s", exc)
            return None

    def _save_concurso_json(self, concurso: int, raw: dict) -> None:
        path = self.data_dir / f"concurso_{concurso}.json"
        if not path.exists():
            path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")

    # -- Public interface -------------------------------------------------------

    def fetch_all_results(self) -> List[dict]:
        """Load all draws: first from local files, persist to DB, return list."""
        records = self._load_local_files()
        for rec in records:
            self.db.upsert_concurso(rec["concurso"], rec["data"], rec["dezenas"], rec["raw"])
        return self.db.get_all_concursos()

    def fetch_latest(self) -> Optional[dict]:
        rec = self._fetch_latest_api()
        if rec is None:
            return self.db.get_latest_concurso()
        self.db.upsert_concurso(rec["concurso"], rec["data"], rec["dezenas"], rec["raw"])
        self._save_concurso_json(rec["concurso"], rec["raw"])
        return {"concurso": rec["concurso"], "data": rec["data"], "dezenas": rec["dezenas"]}

    def fetch_by_concurso(self, numero: int) -> Optional[dict]:
        all_concursos = self.db.get_all_concursos()
        existing = {r["concurso"]: r for r in all_concursos}
        if numero in existing:
            return existing[numero]
        rec = self._fetch_concurso_api(numero)
        if rec:
            self.db.upsert_concurso(rec["concurso"], rec["data"], rec["dezenas"], rec["raw"])
            return {"concurso": rec["concurso"], "data": rec["data"], "dezenas": rec["dezenas"]}
        return None

    def sync_new_draws(self) -> int:
        """Sync any draws newer than what's in the DB.

        If the DB is empty, bootstraps from local JSON files first (dados/
        already has concurso_*.json files, e.g. from a prior fetch_latest
        or a manual copy) before checking the API for anything newer.
        """
        if self.db.count_concursos() == 0:
            self.fetch_all_results()

        latest_local = self.db.get_latest_concurso()
        latest_api = self._fetch_latest_api()
        if latest_api is None:
            return 0
        start = (latest_local["concurso"] + 1) if latest_local else 1
        end = latest_api["concurso"]
        new_count = 0
        for num in range(start, end + 1):
            rec = self._fetch_concurso_api(num)
            if rec:
                self.db.upsert_concurso(rec["concurso"], rec["data"], rec["dezenas"], rec["raw"])
                self._save_concurso_json(rec["concurso"], rec["raw"])
                new_count += 1
        logger.info("Synced %d new draws (up to concurso %d)", new_count, end)
        return new_count
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd quina && source venv/bin/activate && pytest testes/integracao/test_api_caixa.py -v`
Expected: PASS — all 10 tests green.

- [ ] **Step 5: Commit**

```bash
cd "$(git rev-parse --show-toplevel)"
git add quina/src/quina/infra/dados/api_caixa.py quina/testes/integracao/test_api_caixa.py
git commit -m "$(cat <<'EOF'
feat(quina): add Caixa API fetcher with retry and DB sync

sync_new_draws() bootstraps an empty DB from local JSON files before
checking the API, fixing a first-run gap present in the equivalent
lotofacil code (which returns 0 and never populates the DB when the
local DB starts empty).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: CLI

**Files:**
- Create: `quina/src/quina/interface/cli/dados.py`
- Create: `quina/src/quina/interface/cli/app.py`
- Test: `quina/testes/integracao/test_cli_dados.py`

**Interfaces:**
- Consumes: `QuinaFetcher` from `quina.infra.dados.api_caixa` (Task 7), `DatabaseManager` from `quina.infra.dados.banco` (Task 5).
- Produces: `quina.interface.cli.dados.app` (Typer sub-app with `atualizar` and `status` commands), `quina.interface.cli.app.app` (Typer root app, `quina` entry point, mounts `dados_app` under `dados`).

- [ ] **Step 1: Write the failing test**

File: `quina/testes/integracao/test_cli_dados.py`

```python
from functools import partial

import responses
from typer.testing import CliRunner

from quina.infra.config import API_QUINA
from quina.infra.dados.banco import DatabaseManager
from quina.interface.cli import dados as dados_cli

runner = CliRunner()

RAW_7059 = {"concurso": 7059, "data": "07/07/2026", "dezenas": ["27", "47", "57", "70", "78"]}


def _patch_backends(monkeypatch, tmp_path):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(dados_cli, "DatabaseManager", partial(DatabaseManager, db_path=db_path))
    monkeypatch.setattr(
        dados_cli,
        "QuinaFetcher",
        partial(dados_cli.QuinaFetcher, db=DatabaseManager(db_path=db_path), data_dir=tmp_path),
    )
    return db_path


class TestStatusCommand:
    def test_status_empty_db(self, monkeypatch, tmp_path):
        _patch_backends(monkeypatch, tmp_path)
        result = runner.invoke(dados_cli.app, ["status"])
        assert result.exit_code == 0
        assert "Nenhum concurso" in result.stdout

    def test_status_with_data(self, monkeypatch, tmp_path):
        db_path = _patch_backends(monkeypatch, tmp_path)
        db = DatabaseManager(db_path=db_path)
        db.upsert_concurso(7059, "07/07/2026", [27, 47, 57, 70, 78])

        result = runner.invoke(dados_cli.app, ["status"])

        assert result.exit_code == 0
        assert "7059" in result.stdout


class TestAtualizarCommand:
    # test_atualizar_fetches_new seeds concurso 7058 before mocking `/latest`
    # so sync_new_draws() only needs to fetch a 1-concurso gap. An earlier
    # version of this test started from a fully empty DB, which drove
    # sync_new_draws()'s empty-DB bootstrap into a ~7059-iteration loop with
    # only `/latest` mocked — every other concurso call raised under
    # `responses`, and tenacity's retry (5 attempts, real wait_exponential
    # sleeps, not mocked) turned that into an ~29-hour test. Always seed a
    # prior concurso here, mirroring test_sync_new_draws_fetches_gap in
    # test_api_caixa.py (Task 7).
    @responses.activate
    def test_atualizar_fetches_new(self, monkeypatch, tmp_path):
        db_path = _patch_backends(monkeypatch, tmp_path)
        db = DatabaseManager(db_path=db_path)
        db.upsert_concurso(7058, "06/07/2026", [8, 26, 27, 66, 79])
        responses.add(responses.GET, f"{API_QUINA}/latest", json=RAW_7059, status=200)
        responses.add(responses.GET, f"{API_QUINA}/7059", json=RAW_7059, status=200)

        result = runner.invoke(dados_cli.app, ["atualizar"])

        assert result.exit_code == 0
        assert "sincronizado" in result.stdout

    @responses.activate
    def test_atualizar_already_up_to_date(self, monkeypatch, tmp_path):
        db_path = _patch_backends(monkeypatch, tmp_path)
        db = DatabaseManager(db_path=db_path)
        db.upsert_concurso(7059, "07/07/2026", [27, 47, 57, 70, 78])
        responses.add(responses.GET, f"{API_QUINA}/latest", json=RAW_7059, status=200)

        result = runner.invoke(dados_cli.app, ["atualizar"])

        assert result.exit_code == 0
        assert "já atualizados" in result.stdout
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd quina && source venv/bin/activate && pytest testes/integracao/test_cli_dados.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'quina.interface.cli.dados'`

- [ ] **Step 3: Write the implementation**

File: `quina/src/quina/interface/cli/dados.py`

```python
"""dados subcommands — sync and status for Quina draws."""
from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from quina.infra.dados.api_caixa import QuinaFetcher
from quina.infra.dados.banco import DatabaseManager

app = typer.Typer(help="Gerenciamento de dados — coleta e status.")
console = Console()


@app.command()
def atualizar() -> None:
    """Sincroniza concursos novos da API da Caixa com o banco local."""
    fetcher = QuinaFetcher()
    console.print("[cyan]Verificando concursos novos na API...[/cyan]")
    novos = fetcher.sync_new_draws()
    if novos:
        console.print(f"[green]OK {novos} concurso(s) sincronizado(s)[/green]")
    else:
        console.print("[dim]Dados: já atualizados[/dim]")


@app.command()
def status() -> None:
    """Mostra total de concursos e o último concurso sincronizado."""
    db = DatabaseManager()
    total = db.count_concursos()
    if total == 0:
        console.print("[yellow]Nenhum concurso encontrado no banco.[/yellow]")
        console.print("Execute: [cyan]quina dados atualizar[/cyan]")
        raise typer.Exit(0)

    latest = db.get_latest_concurso()
    table = Table(show_header=False, box=None)
    table.add_row("Total de concursos:", str(total))
    table.add_row("Último concurso:", str(latest["concurso"]))
    table.add_row("Data:", latest["data"])
    table.add_row("Dezenas:", "  ".join(f"{n:02d}" for n in latest["dezenas"]))
    console.print(table)
```

File: `quina/src/quina/interface/cli/app.py`

```python
"""Unified CLI entry point for the Quina Prediction System."""
from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent.parent.parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import typer
from rich.console import Console

from quina.interface.cli.dados import app as dados_app

app = typer.Typer(
    name="quina",
    help="Sistema de previsão Quina — dados, modelos, portfólio e experimentos.",
    add_completion=False,
)
console = Console()

app.add_typer(dados_app, name="dados")


if __name__ == "__main__":
    app()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd quina && source venv/bin/activate && pytest testes/integracao/test_cli_dados.py -v`
Expected: PASS — all 4 tests green.

- [ ] **Step 5: Commit**

```bash
cd "$(git rev-parse --show-toplevel)"
git add quina/src/quina/interface/cli/dados.py quina/src/quina/interface/cli/app.py quina/testes/integracao/test_cli_dados.py
git commit -m "$(cat <<'EOF'
feat(quina): add CLI (quina dados atualizar/status)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 9: Final Verification

**Files:** none (verification only)

**Interfaces:** none — this task exercises everything built in Tasks 1-8 end to end.

- [ ] **Step 1: Reinstall to pick up the `quina` console script**

```bash
cd quina
source venv/bin/activate
pip install -e ".[dev]"
```

Expected: no errors; `Successfully installed quina-prediction-0.1.0` (or "already installed" on re-run).

- [ ] **Step 2: Run the full test suite**

```bash
pytest -v
```

Expected: all tests from Tasks 2–8 pass (regras: 18, entidades: 8, config: 3, banco: 9, leitor: 9, api_caixa: 10, cli_dados: 4 — 61 tests total), 0 failures.

- [ ] **Step 3: Manual smoke test against the real API**

```bash
quina dados status
quina dados atualizar
quina dados status
```

Expected: first `status` reports "Nenhum concurso encontrado" (DB is empty — `dados/` only has the symlink, no `concurso_*.json` yet). `atualizar` reports N concursos synchronized (the full historical backfill, since `latest_local` starts `None` → `start=1`; this will make ~7000 sequential API calls and take a while — if that's undesired for this smoke test, seed `dados/` first by copying a few files from `testes/fixtures/sample_draws/` into `dados/` before running `atualizar`, so it only backfills a handful of concursos instead of the full history). Second `status` shows the total count and the latest concurso with 5 dezenas.

- [ ] **Step 4: Verify the fixture data is committed and `dados/` is not**

```bash
cd "$(git rev-parse --show-toplevel)"
git status --short quina/
git ls-files quina/dados
```

Expected: `git status` shows no untracked/modified files under `quina/` (everything from Tasks 1–8 already committed); `git ls-files quina/dados` prints nothing (the symlink was never staged, `.gitignore` excludes it).

No commit for this task — it's verification only, not a code change.

---

## Self-Review Notes

- **Spec coverage:** every section of `docs/superpowers/specs/2026-07-07-quina-fundacao-design.md` maps to a task — architecture/scaffold (Task 1), domain rules (Task 2), entities (Task 3), config (Task 4), database (Task 5), local reader (Task 6, mentioned in spec's `infra/dados/leitor.py` bullet), API fetcher (Task 7), CLI (Task 8), sample data correction (Task 1 Step 5, using the corrected `testes/fixtures/sample_draws/` location).
- **Placeholder scan:** no TBD/TODO/"add validation later" — every step has runnable code.
- **Type consistency:** `DatabaseManager.get_latest_concurso()`/`get_all_concursos()` return shape (`{"concurso", "data", "dezenas"}`) is identical across Task 5 (definition), Task 7 (`QuinaFetcher.fetch_by_concurso`/`fetch_latest` return the same shape), and Task 8 (CLI reads `latest["concurso"]`, `latest["data"]`, `latest["dezenas"]`) — consistent throughout.
- **Fora de escopo** (per spec, confirmed not touched by any task): feature engineering, ML models, backtest, portfolio generation, additional CLI commands, the dashboard, and the scheduler.
