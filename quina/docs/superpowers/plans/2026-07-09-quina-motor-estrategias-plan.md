# Quina — Motor Estatístico + Gerador de Jogos Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a statistical/heuristic strategy engine and game generator for the Quina project — combinatorial filters, weighted frequency/atraso, wheeling (fechamento), budget-based portfolio, and a walk-forward backtest ("treino") — exposed via CLI and synchronous Flask routes, per `docs/superpowers/specs/2026-07-09-quina-motor-estrategias-design.md`.

**Architecture:** New `servicos/` package (mirrors `lotofacil/src/lotofacil/servicos/`) sits between `dominio/` and `interface/`. All strategy functions operate on `draws: list[dict]` in the exact shape `DatabaseManager.get_all_concursos()` already returns (`{"concurso": int, "data": str, "dezenas": list[int]}`) — no new draw representation is introduced. Persistence adds two SQLite tables (`estrategias_backtest`, `jogos_gerados`) to the existing `DatabaseManager`. CLI adds three new Typer sub-apps (`modelo`, `jogos`, `portfolio`); Flask adds routes that call the same service functions synchronously, returning a `job_id` string as a forward-compatible hook (no real queue).

**Tech Stack:** Python 3.11+, stdlib only for the new logic (`random`, `itertools`, `statistics`, `time`, `math.comb`) — no new dependencies. Existing stack: `typer`, `rich`, `flask`, `pytest`.

## Global Constraints

- `TOTAL_NUMEROS = 80`, `NUMEROS_POR_SORTEIO = 5`, `FAIXAS_ACERTOS = [2, 3, 4, 5]` (from `quina/dominio/regras.py` — do not redefine, import).
- `TAMANHO_APOSTA_MIN = 5`, `TAMANHO_APOSTA_MAX = 15` (this plan).
- `PRECO_APOSTA_MINIMA = 3.00` (aposta mínima de 5 dezenas — confirmado pelo usuário em 2026-07-09).
- **Deviation from the design doc, documented here:** `PRECO_APOSTA_MINIMA` and `custo_aposta()` live in `dominio/regras.py`, not `infra/config.py`. Putting a price constant used by a domain rule in the infra layer would make `dominio` depend on `infra`, inverting the project's existing layering (`dominio` has zero imports from `infra` today). `regras.py` already hosts other game-rule constants (`TOTAL_NUMEROS`, `FAIXAS_ACERTOS`), so the price constant belongs there too.
- All new service functions accept `draws: list[dict]` with keys `concurso`, `data`, `dezenas` — the same shape as `DatabaseManager.get_all_concursos()`. Do not introduce `Sorteio` (pydantic) or `SorteioArquivo` (dataclass) into `servicos/`.
- No new external dependencies in `pyproject.toml`.
- Tests: `pytest` (configured via `testpaths = ["testes"]` in `quina/pyproject.toml`). Unit tests → `testes/unidade/`, integration tests (DB, Flask, CLI, fixtures) → `testes/integracao/`.
- Follow existing project conventions: Portuguese names for domain/service code and CLI commands, English is fine in code comments only where already used (there are none — the codebase has none; do not add any beyond what's needed).

---

## File Structure

```
quina/src/quina/
├── dominio/
│   └── regras.py                          # MODIFY: + custo_aposta, TAMANHO_APOSTA_MIN/MAX, PRECO_APOSTA_MINIMA
├── infra/dados/
│   ├── banco.py                           # MODIFY: + 2 tables, 5 new methods
│   └── api_caixa.py                       # MODIFY: sync_new_draws validates pending jogos_gerados
├── servicos/                              # NEW package
│   ├── __init__.py                        # NEW
│   ├── estrategias/
│   │   ├── __init__.py                    # NEW
│   │   ├── filtros.py                     # NEW: 7 pure scoring functions
│   │   ├── scoring.py                     # NEW: gerar_candidatos, top_k
│   │   └── frequencia_atraso.py           # NEW: weighted frequency+atraso scoring
│   ├── fechamento.py                      # NEW: greedy wheeling
│   ├── backtest.py                        # NEW: walk-forward backtest
│   └── portfolio.py                       # NEW: budget-based portfolio
└── interface/
    ├── cli/
    │   ├── app.py                         # MODIFY: register modelo/jogos/portfolio sub-apps
    │   ├── modelo.py                      # NEW: `quina modelo treinar|leaderboard`
    │   ├── jogos.py                       # NEW: `quina jogos gerar|fechamento`
    │   └── portfolio.py                   # NEW: `quina portfolio gerar`
    └── painel/
        └── server.py                      # MODIFY: + /api/treinos, /api/jogos, /api/fechamento, /api/portfolio

quina/testes/
├── unidade/
│   ├── test_regras.py                     # MODIFY: + TestCustoAposta
│   └── test_filtros.py                    # NEW
├── integracao/
│   ├── test_api_caixa.py                  # MODIFY: + TestSyncValidaJogosGerados
│   ├── test_banco_estrategias.py          # NEW
│   ├── test_scoring.py                    # NEW
│   ├── test_frequencia_atraso.py          # NEW
│   ├── test_fechamento.py                 # NEW
│   ├── test_backtest.py                   # NEW
│   ├── test_portfolio.py                  # NEW
│   ├── test_server_estrategias.py         # NEW
│   ├── test_cli_modelo.py                 # NEW
│   ├── test_cli_jogos.py                  # NEW
│   └── test_cli_portfolio.py              # NEW
```

---

### Task 1: Regras de domínio — tamanho de aposta e custo

**Files:**
- Modify: `quina/src/quina/dominio/regras.py`
- Test: `quina/testes/unidade/test_regras.py`

**Interfaces:**
- Produces: `TAMANHO_APOSTA_MIN: int = 5`, `TAMANHO_APOSTA_MAX: int = 15`, `PRECO_APOSTA_MINIMA: float = 3.00`, `custo_aposta(n: int) -> float` (raises `ValueError` if `n` outside `[TAMANHO_APOSTA_MIN, TAMANHO_APOSTA_MAX]`).

- [ ] **Step 1: Write the failing tests**

Append to `quina/testes/unidade/test_regras.py` (add this import to the existing `from quina.dominio.regras import (...)` block and this new class at the end of the file):

```python
# Add to the existing import block at the top of the file:
#   custo_aposta,
#   TAMANHO_APOSTA_MIN,
#   TAMANHO_APOSTA_MAX,

import pytest


class TestCustoAposta:
    def test_aposta_minima_5_dezenas(self):
        assert custo_aposta(5) == 3.00

    def test_aposta_6_dezenas(self):
        assert custo_aposta(6) == 18.00  # comb(6,5)=6 * 3.00

    def test_aposta_maxima_15_dezenas(self):
        assert custo_aposta(15) == 9009.00  # comb(15,5)=3003 * 3.00

    def test_abaixo_do_minimo_levanta_erro(self):
        with pytest.raises(ValueError):
            custo_aposta(4)

    def test_acima_do_maximo_levanta_erro(self):
        with pytest.raises(ValueError):
            custo_aposta(16)

    def test_constantes(self):
        assert TAMANHO_APOSTA_MIN == 5
        assert TAMANHO_APOSTA_MAX == 15
```

The full updated import block at the top of the file should read:

```python
from quina.dominio.regras import (
    FAIXAS_ACERTOS,
    NUMEROS_POR_SORTEIO,
    TAMANHO_APOSTA_MAX,
    TAMANHO_APOSTA_MIN,
    TOTAL_NUMEROS,
    VALID_NUMBERS,
    contar_acertos,
    contar_impares,
    contar_pares,
    custo_aposta,
    estatisticas_dezenas,
    gerar_combinacoes,
    repetidos_anterior,
    soma_dezenas,
    total_combinacoes,
    validar_dezenas,
)
import pytest
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd quina && source venv/bin/activate && pytest testes/unidade/test_regras.py -v`
Expected: FAIL with `ImportError: cannot import name 'custo_aposta'`

- [ ] **Step 3: Implement in regras.py**

Append to `quina/src/quina/dominio/regras.py` (after `total_combinacoes`):

```python
PRECO_APOSTA_MINIMA = 3.00

TAMANHO_APOSTA_MIN = NUMEROS_POR_SORTEIO
TAMANHO_APOSTA_MAX = 15


def custo_aposta(n: int) -> float:
    """Custo de uma aposta de n dezenas: comb(n, 5) apostas de 5 dezenas embutidas."""
    if not (TAMANHO_APOSTA_MIN <= n <= TAMANHO_APOSTA_MAX):
        raise ValueError(
            f"Tamanho de aposta deve estar entre {TAMANHO_APOSTA_MIN} e {TAMANHO_APOSTA_MAX}, recebido {n}"
        )
    return round(comb(n, NUMEROS_POR_SORTEIO) * PRECO_APOSTA_MINIMA, 2)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd quina && source venv/bin/activate && pytest testes/unidade/test_regras.py -v`
Expected: PASS (all tests including the new `TestCustoAposta` class)

- [ ] **Step 5: Commit**

```bash
git add quina/src/quina/dominio/regras.py quina/testes/unidade/test_regras.py
git commit -m "feat(quina): add variable bet size and cost calculation to domain rules"
```

---

### Task 2: Persistência — tabelas `estrategias_backtest` e `jogos_gerados`

**Files:**
- Modify: `quina/src/quina/infra/dados/banco.py`
- Test: `quina/testes/integracao/test_banco_estrategias.py`

**Interfaces:**
- Consumes: nothing new.
- Produces:
  - `DatabaseManager.salvar_backtest(estrategia: str, janela: int, metricas: dict) -> int`
  - `DatabaseManager.listar_backtests(limite: int = 20) -> list[dict]` — each `{"id", "estrategia", "janela", "metricas", "criado_em"}`
  - `DatabaseManager.salvar_jogo_gerado(estrategia: str, tamanho_aposta: int, dezenas: list[int], score: float | None, custo: float, concurso_alvo_validacao: int | None = None) -> int`
  - `DatabaseManager.listar_jogos_gerados(limite: int = 50, offset: int = 0) -> list[dict]` — each `{"id", "estrategia", "tamanho_aposta", "dezenas", "score", "custo", "criado_em", "concurso_alvo_validacao", "acertos"}`
  - `DatabaseManager.atualizar_acertos_pendentes(concurso: int, dezenas_sorteadas: list[int]) -> int` — returns count of rows updated

- [ ] **Step 1: Write the failing tests**

Create `quina/testes/integracao/test_banco_estrategias.py`:

```python
import sqlite3

import pytest

from quina.infra.dados.banco import DatabaseManager


@pytest.fixture
def db(tmp_path):
    return DatabaseManager(db_path=tmp_path / "test_estrategias.db")


class TestTabelasNovas:
    def test_estrategias_backtest_table_exists(self, db):
        conn = sqlite3.connect(db.db_path)
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='estrategias_backtest'"
        ).fetchone()
        conn.close()
        assert row is not None

    def test_jogos_gerados_table_exists(self, db):
        conn = sqlite3.connect(db.db_path)
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='jogos_gerados'"
        ).fetchone()
        conn.close()
        assert row is not None


class TestSalvarBacktest:
    def test_salvar_e_listar(self, db):
        metricas = {"taxa_estrategia": {"2": 0.1, "3": 0.0, "4": 0.0, "5": 0.0}}
        backtest_id = db.salvar_backtest("filtros", 300, metricas)
        assert backtest_id is not None

        registros = db.listar_backtests()
        assert len(registros) == 1
        assert registros[0]["estrategia"] == "filtros"
        assert registros[0]["janela"] == 300
        assert registros[0]["metricas"] == metricas

    def test_listar_ordenado_do_mais_recente(self, db):
        db.salvar_backtest("filtros", 100, {"a": 1})
        db.salvar_backtest("frequencia_atraso", 200, {"b": 2})

        registros = db.listar_backtests()

        assert registros[0]["estrategia"] == "frequencia_atraso"
        assert registros[1]["estrategia"] == "filtros"

    def test_limite(self, db):
        for i in range(5):
            db.salvar_backtest("filtros", i, {"i": i})

        registros = db.listar_backtests(limite=2)

        assert len(registros) == 2


class TestJogosGerados:
    def test_salvar_e_listar(self, db):
        jogo_id = db.salvar_jogo_gerado(
            estrategia="filtros", tamanho_aposta=5, dezenas=[1, 2, 3, 4, 5],
            score=0.75, custo=3.0,
        )
        assert jogo_id is not None

        jogos = db.listar_jogos_gerados()
        assert len(jogos) == 1
        assert jogos[0]["dezenas"] == [1, 2, 3, 4, 5]
        assert jogos[0]["score"] == 0.75
        assert jogos[0]["custo"] == 3.0
        assert jogos[0]["acertos"] is None
        assert jogos[0]["concurso_alvo_validacao"] is None

    def test_salvar_com_concurso_alvo(self, db):
        db.salvar_jogo_gerado(
            estrategia="filtros", tamanho_aposta=5, dezenas=[1, 2, 3, 4, 5],
            score=0.75, custo=3.0, concurso_alvo_validacao=7060,
        )
        jogos = db.listar_jogos_gerados()
        assert jogos[0]["concurso_alvo_validacao"] == 7060

    def test_listar_com_paginacao(self, db):
        for i in range(5):
            db.salvar_jogo_gerado(
                estrategia="filtros", tamanho_aposta=5, dezenas=[1, 2, 3, 4, 5 + i],
                score=0.5, custo=3.0,
            )
        pagina = db.listar_jogos_gerados(limite=2, offset=2)
        assert len(pagina) == 2


class TestAtualizarAcertosPendentes:
    def test_atualiza_jogo_pendente(self, db):
        db.salvar_jogo_gerado(
            estrategia="filtros", tamanho_aposta=5, dezenas=[27, 47, 57, 70, 78],
            score=0.8, custo=3.0, concurso_alvo_validacao=7059,
        )

        atualizados = db.atualizar_acertos_pendentes(7059, [27, 47, 57, 70, 78])

        assert atualizados == 1
        jogos = db.listar_jogos_gerados()
        assert jogos[0]["acertos"] == 5

    def test_nao_atualiza_concurso_diferente(self, db):
        db.salvar_jogo_gerado(
            estrategia="filtros", tamanho_aposta=5, dezenas=[27, 47, 57, 70, 78],
            score=0.8, custo=3.0, concurso_alvo_validacao=9999,
        )

        atualizados = db.atualizar_acertos_pendentes(7059, [27, 47, 57, 70, 78])

        assert atualizados == 0

    def test_acertos_parciais(self, db):
        db.salvar_jogo_gerado(
            estrategia="filtros", tamanho_aposta=5, dezenas=[1, 2, 3, 47, 78],
            score=0.8, custo=3.0, concurso_alvo_validacao=7059,
        )

        db.atualizar_acertos_pendentes(7059, [27, 47, 57, 70, 78])

        jogos = db.listar_jogos_gerados()
        assert jogos[0]["acertos"] == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd quina && source venv/bin/activate && pytest testes/integracao/test_banco_estrategias.py -v`
Expected: FAIL with `AttributeError: 'DatabaseManager' object has no attribute 'salvar_backtest'`

- [ ] **Step 3: Implement in banco.py**

Modify the `_init_db` method's `executescript` call (currently `quina/src/quina/infra/dados/banco.py:35-55`) to add the two new tables after the existing `predicoes` table definition, so the full script reads:

```python
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

                CREATE TABLE IF NOT EXISTS estrategias_backtest (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    estrategia      TEXT NOT NULL,
                    janela          INTEGER NOT NULL,
                    metricas_json   TEXT NOT NULL,
                    criado_em       TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS jogos_gerados (
                    id                       INTEGER PRIMARY KEY AUTOINCREMENT,
                    estrategia               TEXT NOT NULL,
                    tamanho_aposta           INTEGER NOT NULL,
                    dezenas_json             TEXT NOT NULL,
                    score                    REAL,
                    custo                    REAL NOT NULL,
                    criado_em                TEXT DEFAULT (datetime('now')),
                    concurso_alvo_validacao  INTEGER,
                    acertos                  INTEGER
                );
            """)
        logger.debug("Database initialised at %s", self.db_path)
```

Append these new methods at the end of the `DatabaseManager` class (after `get_latest_concurso`, currently ending at `quina/src/quina/infra/dados/banco.py:104`):

```python
    # -- Estrategias / backtest --------------------------------------------------

    def salvar_backtest(self, estrategia: str, janela: int, metricas: dict) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO estrategias_backtest (estrategia, janela, metricas_json) VALUES (?, ?, ?)",
                (estrategia, janela, json.dumps(metricas)),
            )
        return cur.lastrowid

    def listar_backtests(self, limite: int = 20) -> List[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT id, estrategia, janela, metricas_json, criado_em
                   FROM estrategias_backtest ORDER BY id DESC LIMIT ?""",
                (limite,),
            ).fetchall()
        return [
            {
                "id": r["id"],
                "estrategia": r["estrategia"],
                "janela": r["janela"],
                "metricas": json.loads(r["metricas_json"]),
                "criado_em": r["criado_em"],
            }
            for r in rows
        ]

    # -- Jogos gerados ------------------------------------------------------------

    def salvar_jogo_gerado(
        self,
        estrategia: str,
        tamanho_aposta: int,
        dezenas: List[int],
        score: Optional[float],
        custo: float,
        concurso_alvo_validacao: Optional[int] = None,
    ) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                """INSERT INTO jogos_gerados
                   (estrategia, tamanho_aposta, dezenas_json, score, custo, concurso_alvo_validacao)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (estrategia, tamanho_aposta, json.dumps(sorted(dezenas)), score, custo, concurso_alvo_validacao),
            )
        return cur.lastrowid

    def listar_jogos_gerados(self, limite: int = 50, offset: int = 0) -> List[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT id, estrategia, tamanho_aposta, dezenas_json, score, custo,
                          criado_em, concurso_alvo_validacao, acertos
                   FROM jogos_gerados ORDER BY id DESC LIMIT ? OFFSET ?""",
                (limite, offset),
            ).fetchall()
        return [
            {
                "id": r["id"],
                "estrategia": r["estrategia"],
                "tamanho_aposta": r["tamanho_aposta"],
                "dezenas": json.loads(r["dezenas_json"]),
                "score": r["score"],
                "custo": r["custo"],
                "criado_em": r["criado_em"],
                "concurso_alvo_validacao": r["concurso_alvo_validacao"],
                "acertos": r["acertos"],
            }
            for r in rows
        ]

    def atualizar_acertos_pendentes(self, concurso: int, dezenas_sorteadas: List[int]) -> int:
        sorteadas = set(dezenas_sorteadas)
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, dezenas_json FROM jogos_gerados WHERE concurso_alvo_validacao = ? AND acertos IS NULL",
                (concurso,),
            ).fetchall()
            for r in rows:
                dezenas_jogo = json.loads(r["dezenas_json"])
                acertos = len(set(dezenas_jogo) & sorteadas)
                conn.execute("UPDATE jogos_gerados SET acertos = ? WHERE id = ?", (acertos, r["id"]))
        return len(rows)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd quina && source venv/bin/activate && pytest testes/integracao/test_banco_estrategias.py testes/integracao/test_banco.py -v`
Expected: PASS (new tests and the existing `test_banco.py` suite, unaffected)

- [ ] **Step 5: Commit**

```bash
git add quina/src/quina/infra/dados/banco.py quina/testes/integracao/test_banco_estrategias.py
git commit -m "feat(quina): add estrategias_backtest and jogos_gerados tables"
```

---

### Task 3: Filtros combinatórios de scoring

**Files:**
- Create: `quina/src/quina/servicos/__init__.py`
- Create: `quina/src/quina/servicos/estrategias/__init__.py`
- Create: `quina/src/quina/servicos/estrategias/filtros.py`
- Test: `quina/testes/unidade/test_filtros.py`

**Interfaces:**
- Consumes: `NUMEROS_POR_SORTEIO`, `TOTAL_NUMEROS` from `quina.dominio.regras`.
- Produces (all pure functions, each returns `float` in `[0.0, 1.0]`):
  - `score_soma(dezenas: list[int], draws: list[dict]) -> float`
  - `score_paridade(dezenas: list[int]) -> float`
  - `score_quadrantes(dezenas: list[int]) -> float`
  - `score_primos(dezenas: list[int]) -> float`
  - `score_repeticao(dezenas: list[int], draws: list[dict]) -> float`
  - `score_consecutivos(dezenas: list[int], draws: list[dict]) -> float`
  - `score_anti_popularidade(dezenas: list[int]) -> float`

- [ ] **Step 1: Write the failing tests**

Create `quina/testes/unidade/test_filtros.py`:

```python
from quina.servicos.estrategias import filtros


def _draws(*listas_dezenas):
    return [{"concurso": i + 1, "data": "", "dezenas": d} for i, d in enumerate(listas_dezenas)]


class TestScoreSoma:
    def test_soma_igual_a_media_historica_escalada_e_score_maximo(self):
        draws = _draws([10, 20, 30, 40, 50])  # soma=150, unica amostra -> desvio=0 -> fallback 1.0
        candidato = [10, 20, 30, 40, 50]  # soma=150, mesmo fator (n=5)
        assert filtros.score_soma(candidato, draws) == 1.0

    def test_soma_muito_distante_da_media_e_score_minimo(self):
        draws = _draws([10, 20, 30, 40, 50])  # media=150, desvio fallback=1.0
        candidato = [41, 42, 43, 44, 80]  # soma=250, diff=100 >> 2*1.0
        assert filtros.score_soma(candidato, draws) == 0.0


class TestScoreParidade:
    def test_equilibrado_e_score_maximo(self):
        assert filtros.score_paridade([1, 2, 3, 4]) == 1.0  # 2 pares, 2 impares, ideal=2

    def test_todos_pares_e_score_minimo(self):
        assert filtros.score_paridade([2, 4, 6, 8]) == 0.0  # 4 pares, ideal=2, desvio max


class TestScoreQuadrantes:
    def test_um_por_quadrante_e_score_maximo(self):
        assert filtros.score_quadrantes([10, 30, 50, 70]) == 1.0

    def test_todos_no_mesmo_quadrante_e_score_minimo(self):
        assert filtros.score_quadrantes([1, 2, 3, 4]) == 0.0


class TestScorePrimos:
    def test_proporcao_igual_ao_universo_e_score_maximo(self):
        candidato = list(range(1, 81))  # 22 primos em 80 = mesma proporcao do universo
        assert filtros.score_primos(candidato) == 1.0

    def test_so_primos_e_score_minimo(self):
        assert filtros.score_primos([2, 3, 5, 7, 11]) == 0.0


class TestScoreRepeticao:
    def test_sem_sobreposicao_historica_e_sem_sobreposicao_no_candidato_e_score_maximo(self):
        draws = _draws([1, 2, 3, 4, 5], [6, 7, 8, 9, 10])  # 0 overlap entre os 2 sorteios
        candidato = [1, 2, 3, 4, 5]  # 0 overlap com o ultimo sorteio [6..10]
        assert filtros.score_repeticao(candidato, draws) == 1.0

    def test_repeticao_total_quando_esperado_e_zero_e_score_minimo(self):
        draws = _draws([1, 2, 3, 4, 5], [6, 7, 8, 9, 10])
        candidato = [6, 7, 8, 9, 10]  # repete 100% do ultimo sorteio
        assert filtros.score_repeticao(candidato, draws) == 0.0


class TestScoreConsecutivos:
    def test_sem_consecutivos_historicos_e_sem_consecutivos_no_candidato_e_score_maximo(self):
        draws = _draws([1, 3, 5, 7, 9])  # 0 pares consecutivos
        candidato = [10, 20, 30, 40, 50]  # 0 pares consecutivos
        assert filtros.score_consecutivos(candidato, draws) == 1.0

    def test_totalmente_consecutivo_quando_esperado_e_zero_e_score_minimo(self):
        draws = _draws([1, 3, 5, 7, 9])
        candidato = [1, 2, 3, 4, 5]  # 4 pares consecutivos
        assert filtros.score_consecutivos(candidato, draws) == 0.0


class TestScoreAntiPopularidade:
    def test_sem_numeros_populares_e_score_maximo(self):
        assert filtros.score_anti_popularidade([40, 50, 60, 70, 80]) == 1.0

    def test_so_numeros_populares_e_score_minimo(self):
        assert filtros.score_anti_popularidade([1, 2, 3, 4, 5]) == 0.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd quina && source venv/bin/activate && pytest testes/unidade/test_filtros.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'quina.servicos'`

- [ ] **Step 3: Implement**

Create `quina/src/quina/servicos/__init__.py` (empty file).

Create `quina/src/quina/servicos/estrategias/__init__.py` (empty file).

Create `quina/src/quina/servicos/estrategias/filtros.py`:

```python
"""Filtros estatísticos puros para pontuação de candidatos de jogos da Quina.

Cada score_* retorna um valor em [0, 1]: quanto maior, mais o candidato se
aproxima do padrão observado nos sorteios reais — exceto anti_popularidade,
que mede aproximação ao padrão que maximiza valor esperado de prêmio (menos
rateio), não um padrão de frequência histórica.
"""
from __future__ import annotations

import statistics

from quina.dominio.regras import NUMEROS_POR_SORTEIO, TOTAL_NUMEROS

_PRIMOS = frozenset({2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79})
_PROPORCAO_PRIMOS_UNIVERSO = len(_PRIMOS) / TOTAL_NUMEROS

_LIMITE_POPULAR = 31
_PROPORCAO_POPULAR_ESPERADA = _LIMITE_POPULAR / TOTAL_NUMEROS


def score_soma(dezenas: list[int], draws: list[dict]) -> float:
    n = len(dezenas)
    somas_historicas = [sum(d["dezenas"]) for d in draws]
    media_5 = statistics.mean(somas_historicas)
    desvio_5 = statistics.pstdev(somas_historicas) or 1.0

    fator = n / NUMEROS_POR_SORTEIO
    media_esperada = media_5 * fator
    desvio_esperado = desvio_5 * (fator ** 0.5)

    diferenca = abs(sum(dezenas) - media_esperada)
    return max(0.0, 1.0 - diferenca / (2 * desvio_esperado))


def score_paridade(dezenas: list[int]) -> float:
    n = len(dezenas)
    pares = sum(1 for d in dezenas if d % 2 == 0)
    ideal = n / 2
    max_desvio = ideal or 1.0
    return max(0.0, 1.0 - abs(pares - ideal) / max_desvio)


def score_quadrantes(dezenas: list[int]) -> float:
    n = len(dezenas)
    quadrantes = [0, 0, 0, 0]
    for d in dezenas:
        indice = min((d - 1) // 20, 3)
        quadrantes[indice] += 1
    ideal = n / 4
    desvio_total = sum(abs(c - ideal) for c in quadrantes)
    desvio_maximo = 1.5 * n
    return max(0.0, 1.0 - desvio_total / desvio_maximo)


def score_primos(dezenas: list[int]) -> float:
    n = len(dezenas)
    primos = sum(1 for d in dezenas if d in _PRIMOS)
    ideal = n * _PROPORCAO_PRIMOS_UNIVERSO
    max_desvio = max(ideal, n - ideal) or 1.0
    return max(0.0, 1.0 - abs(primos - ideal) / max_desvio)


def score_repeticao(dezenas: list[int], draws: list[dict]) -> float:
    n = len(dezenas)
    if len(draws) < 2:
        taxa_historica = 0.0
    else:
        total_overlap = sum(
            len(set(a["dezenas"]) & set(b["dezenas"]))
            for a, b in zip(draws, draws[1:])
        )
        taxa_historica = total_overlap / (len(draws) - 1) / NUMEROS_POR_SORTEIO

    ultimo_sorteio = set(draws[-1]["dezenas"])
    overlap = len(set(dezenas) & ultimo_sorteio)
    esperado = taxa_historica * n
    max_desvio = max(esperado, n - esperado, 1.0)
    return max(0.0, 1.0 - abs(overlap - esperado) / max_desvio)


def score_consecutivos(dezenas: list[int], draws: list[dict]) -> float:
    n = len(dezenas)
    pares_possiveis = max(n - 1, 1)
    ordenado = sorted(dezenas)
    consecutivos_candidato = sum(1 for a, b in zip(ordenado, ordenado[1:]) if b - a == 1)

    if not draws:
        taxa_historica = 0.0
    else:
        total_consecutivos = 0
        for sorteio in draws:
            ord_s = sorted(sorteio["dezenas"])
            total_consecutivos += sum(1 for a, b in zip(ord_s, ord_s[1:]) if b - a == 1)
        taxa_historica = total_consecutivos / len(draws) / (NUMEROS_POR_SORTEIO - 1)

    esperado = taxa_historica * pares_possiveis
    max_desvio = max(esperado, pares_possiveis - esperado, 1.0)
    return max(0.0, 1.0 - abs(consecutivos_candidato - esperado) / max_desvio)


def score_anti_popularidade(dezenas: list[int]) -> float:
    n = len(dezenas)
    populares = sum(1 for d in dezenas if d <= _LIMITE_POPULAR)
    proporcao = populares / n
    if proporcao <= _PROPORCAO_POPULAR_ESPERADA:
        return 1.0
    excesso = proporcao - _PROPORCAO_POPULAR_ESPERADA
    maximo_excesso = 1.0 - _PROPORCAO_POPULAR_ESPERADA
    return max(0.0, 1.0 - excesso / maximo_excesso)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd quina && source venv/bin/activate && pytest testes/unidade/test_filtros.py -v`
Expected: PASS (all 14 tests)

- [ ] **Step 5: Commit**

```bash
git add quina/src/quina/servicos quina/testes/unidade/test_filtros.py
git commit -m "feat(quina): add combinatorial scoring filters for game candidates"
```

---

### Task 4: Geração e pontuação de candidatos (scoring.py)

**Files:**
- Create: `quina/src/quina/servicos/estrategias/scoring.py`
- Test: `quina/testes/integracao/test_scoring.py`

**Interfaces:**
- Consumes: `TOTAL_NUMEROS` from `quina.dominio.regras`; all `score_*` functions from `quina.servicos.estrategias.filtros` (Task 3).
- Produces:
  - `FILTROS_PADRAO: dict[str, Callable]` — maps filter name to function
  - `gerar_candidatos(quantidade: int, tamanho_aposta: int, draws: list[dict], pesos: dict[str, float] | None = None) -> list[dict]` — each item `{"dezenas": list[int], "score": float, "detalhes": dict[str, float]}`, sorted by `score` descending
  - `top_k(candidatos: list[dict], k: int) -> list[dict]`

(This is `testes/integracao/` rather than `unidade/` because it exercises randomness and multi-filter composition end-to-end, consistent with how `test_leitor.py`/`test_banco.py` are integration-level in this project despite not touching the DB directly — the existing project draws that line at "exercises more than one pure function together".)

- [ ] **Step 1: Write the failing tests**

Create `quina/testes/integracao/test_scoring.py`:

```python
from quina.servicos.estrategias import scoring


def _draws_fixture():
    return [
        {"concurso": 1, "data": "01/01/2026", "dezenas": [1, 2, 3, 4, 5]},
        {"concurso": 2, "data": "02/01/2026", "dezenas": [6, 7, 8, 9, 10]},
        {"concurso": 3, "data": "03/01/2026", "dezenas": [11, 12, 13, 14, 15]},
    ]


class TestGerarCandidatos:
    def test_gera_quantidade_correta(self):
        candidatos = scoring.gerar_candidatos(quantidade=20, tamanho_aposta=5, draws=_draws_fixture())
        assert len(candidatos) == 20

    def test_cada_candidato_tem_tamanho_correto_e_dezenas_validas(self):
        candidatos = scoring.gerar_candidatos(quantidade=10, tamanho_aposta=7, draws=_draws_fixture())
        for c in candidatos:
            assert len(c["dezenas"]) == 7
            assert len(set(c["dezenas"])) == 7
            assert all(1 <= d <= 80 for d in c["dezenas"])
            assert c["dezenas"] == sorted(c["dezenas"])

    def test_candidatos_ordenados_por_score_decrescente(self):
        candidatos = scoring.gerar_candidatos(quantidade=30, tamanho_aposta=5, draws=_draws_fixture())
        scores = [c["score"] for c in candidatos]
        assert scores == sorted(scores, reverse=True)

    def test_score_entre_zero_e_um(self):
        candidatos = scoring.gerar_candidatos(quantidade=30, tamanho_aposta=5, draws=_draws_fixture())
        assert all(0.0 <= c["score"] <= 1.0 for c in candidatos)

    def test_detalhes_tem_todos_os_filtros(self):
        candidatos = scoring.gerar_candidatos(quantidade=1, tamanho_aposta=5, draws=_draws_fixture())
        assert set(candidatos[0]["detalhes"].keys()) == set(scoring.FILTROS_PADRAO.keys())


class TestTopK:
    def test_retorna_k_melhores(self):
        candidatos = [
            {"dezenas": [1, 2, 3, 4, 5], "score": 0.5},
            {"dezenas": [6, 7, 8, 9, 10], "score": 0.9},
            {"dezenas": [11, 12, 13, 14, 15], "score": 0.1},
        ]
        top = scoring.top_k(candidatos, 2)
        assert [c["score"] for c in top] == [0.9, 0.5]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd quina && source venv/bin/activate && pytest testes/integracao/test_scoring.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'quina.servicos.estrategias.scoring'`

- [ ] **Step 3: Implement**

Create `quina/src/quina/servicos/estrategias/scoring.py`:

```python
"""Geração e pontuação de candidatos de jogos da Quina."""
from __future__ import annotations

import random
from typing import Optional

from quina.dominio.regras import TOTAL_NUMEROS
from quina.servicos.estrategias import filtros

FILTROS_PADRAO = {
    "soma": filtros.score_soma,
    "paridade": filtros.score_paridade,
    "quadrantes": filtros.score_quadrantes,
    "primos": filtros.score_primos,
    "repeticao": filtros.score_repeticao,
    "consecutivos": filtros.score_consecutivos,
    "anti_popularidade": filtros.score_anti_popularidade,
}

_FILTROS_QUE_USAM_DRAWS = {"soma", "repeticao", "consecutivos"}


def _pontuar_candidato(
    dezenas: list[int], draws: list[dict], pesos: dict[str, float]
) -> tuple[float, dict[str, float]]:
    detalhes = {}
    for nome in pesos:
        funcao = FILTROS_PADRAO[nome]
        detalhes[nome] = funcao(dezenas, draws) if nome in _FILTROS_QUE_USAM_DRAWS else funcao(dezenas)

    total_pesos = sum(pesos.values())
    score = sum(detalhes[nome] * peso for nome, peso in pesos.items()) / total_pesos
    return round(score, 4), detalhes


def gerar_candidatos(
    quantidade: int,
    tamanho_aposta: int,
    draws: list[dict],
    pesos: Optional[dict[str, float]] = None,
) -> list[dict]:
    if pesos is None:
        pesos = {nome: 1.0 for nome in FILTROS_PADRAO}

    universo = range(1, TOTAL_NUMEROS + 1)
    candidatos = []
    for _ in range(quantidade):
        dezenas = sorted(random.sample(universo, tamanho_aposta))
        score, detalhes = _pontuar_candidato(dezenas, draws, pesos)
        candidatos.append({"dezenas": dezenas, "score": score, "detalhes": detalhes})

    candidatos.sort(key=lambda c: c["score"], reverse=True)
    return candidatos


def top_k(candidatos: list[dict], k: int) -> list[dict]:
    return sorted(candidatos, key=lambda c: c["score"], reverse=True)[:k]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd quina && source venv/bin/activate && pytest testes/integracao/test_scoring.py -v`
Expected: PASS (all 6 tests)

- [ ] **Step 5: Commit**

```bash
git add quina/src/quina/servicos/estrategias/scoring.py quina/testes/integracao/test_scoring.py
git commit -m "feat(quina): add candidate generation and scoring"
```

---

### Task 5: Frequência e atraso ponderados

**Files:**
- Create: `quina/src/quina/servicos/estrategias/frequencia_atraso.py`
- Test: `quina/testes/integracao/test_frequencia_atraso.py`

**Interfaces:**
- Consumes: `TOTAL_NUMEROS` from `quina.dominio.regras`.
- Produces:
  - `pontuar_por_frequencia_atraso(draws: list[dict], peso_freq: float = 0.5, peso_atraso: float = 0.5) -> dict[int, float]`
  - `gerar_candidato_frequencia_atraso(draws: list[dict], tamanho_aposta: int, peso_freq: float = 0.5, peso_atraso: float = 0.5) -> dict` — `{"dezenas": list[int], "score": float}`

- [ ] **Step 1: Write the failing tests**

Create `quina/testes/integracao/test_frequencia_atraso.py`:

```python
from quina.servicos.estrategias.frequencia_atraso import (
    gerar_candidato_frequencia_atraso,
    pontuar_por_frequencia_atraso,
)


def _draws_fixture():
    return [
        {"concurso": 1, "data": "01/01/2026", "dezenas": [1, 2, 3, 4, 5]},
        {"concurso": 2, "data": "02/01/2026", "dezenas": [1, 2, 6, 7, 8]},
        {"concurso": 3, "data": "03/01/2026", "dezenas": [1, 9, 10, 11, 12]},
    ]


class TestPontuarPorFrequenciaAtraso:
    def test_numero_mais_frequente_e_mais_recente(self):
        pontuacoes = pontuar_por_frequencia_atraso(_draws_fixture())
        # numero 1 saiu nos 3 concursos (freq maxima=3) e no ultimo concurso (atraso=0)
        assert pontuacoes[1] == 0.5

    def test_numero_nunca_sorteado_tem_atraso_maximo(self):
        pontuacoes = pontuar_por_frequencia_atraso(_draws_fixture())
        # numero 80 nunca saiu: freq=0 (norm 0.0), atraso=3=max_atraso (norm 1.0)
        assert pontuacoes[80] == 0.5

    def test_pesos_customizados_zeram_componente_de_atraso(self):
        pontuacoes = pontuar_por_frequencia_atraso(_draws_fixture(), peso_freq=1.0, peso_atraso=0.0)
        assert pontuacoes[80] == 0.0  # nunca sorteado, peso_atraso zerado


class TestGerarCandidatoFrequenciaAtraso:
    def test_tamanho_correto(self):
        candidato = gerar_candidato_frequencia_atraso(_draws_fixture(), tamanho_aposta=5)
        assert len(candidato["dezenas"]) == 5
        assert len(set(candidato["dezenas"])) == 5

    def test_numero_mais_frequente_esta_entre_os_escolhidos(self):
        candidato = gerar_candidato_frequencia_atraso(_draws_fixture(), tamanho_aposta=5)
        assert 1 in candidato["dezenas"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd quina && source venv/bin/activate && pytest testes/integracao/test_frequencia_atraso.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement**

Create `quina/src/quina/servicos/estrategias/frequencia_atraso.py`:

```python
"""Pontuação de dezenas por frequência e atraso históricos combinados."""
from __future__ import annotations

from quina.dominio.regras import TOTAL_NUMEROS


def pontuar_por_frequencia_atraso(
    draws: list[dict], peso_freq: float = 0.5, peso_atraso: float = 0.5
) -> dict[int, float]:
    frequencia = {n: 0 for n in range(1, TOTAL_NUMEROS + 1)}
    ultimo_indice: dict[int, int] = {}
    for i, sorteio in enumerate(draws):
        for n in sorteio["dezenas"]:
            frequencia[n] += 1
            ultimo_indice[n] = i

    total = len(draws)
    atraso = {
        n: (total - 1 - ultimo_indice[n]) if n in ultimo_indice else total
        for n in range(1, TOTAL_NUMEROS + 1)
    }

    max_freq = max(frequencia.values()) or 1
    max_atraso = max(atraso.values()) or 1

    return {
        n: round(
            peso_freq * (frequencia[n] / max_freq) + peso_atraso * (atraso[n] / max_atraso),
            4,
        )
        for n in range(1, TOTAL_NUMEROS + 1)
    }


def gerar_candidato_frequencia_atraso(
    draws: list[dict], tamanho_aposta: int, peso_freq: float = 0.5, peso_atraso: float = 0.5
) -> dict:
    pontuacoes = pontuar_por_frequencia_atraso(draws, peso_freq, peso_atraso)
    melhores = sorted(pontuacoes.items(), key=lambda kv: kv[1], reverse=True)[:tamanho_aposta]
    dezenas = sorted(n for n, _ in melhores)
    score = round(sum(p for _, p in melhores) / tamanho_aposta, 4)
    return {"dezenas": dezenas, "score": score}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd quina && source venv/bin/activate && pytest testes/integracao/test_frequencia_atraso.py -v`
Expected: PASS (all 5 tests)

- [ ] **Step 5: Commit**

```bash
git add quina/src/quina/servicos/estrategias/frequencia_atraso.py quina/testes/integracao/test_frequencia_atraso.py
git commit -m "feat(quina): add weighted frequency+atraso scoring strategy"
```

---

### Task 6: Fechamento/wheeling (cobertura greedy)

**Files:**
- Create: `quina/src/quina/servicos/fechamento.py`
- Test: `quina/testes/integracao/test_fechamento.py`

**Interfaces:**
- Consumes: `NUMEROS_POR_SORTEIO`, `custo_aposta` from `quina.dominio.regras` (Task 1).
- Produces: `gerar_fechamento(pool: list[int], garantia: tuple[int, int]) -> dict` — `{"jogos": list[list[int]], "quantidade": int, "custo_total": float}`. Raises `ValueError` for invalid pool/garantia. `LIMITE_POOL = 12` module constant.

- [ ] **Step 1: Write the failing tests**

Create `quina/testes/integracao/test_fechamento.py`:

```python
import pytest

from quina.servicos.fechamento import gerar_fechamento


class TestGerarFechamento:
    def test_pool_do_tamanho_minimo_gera_um_unico_jogo(self):
        resultado = gerar_fechamento([1, 2, 3, 4, 5], garantia=(5, 5))

        assert resultado["quantidade"] == 1
        assert resultado["jogos"] == [[1, 2, 3, 4, 5]]
        assert resultado["custo_total"] == 3.00

    def test_pool_de_6_com_garantia_quina_se_5_saem(self):
        resultado = gerar_fechamento([1, 2, 3, 4, 5, 6], garantia=(5, 5))

        # cada bilhete de 5 so cobre a si mesmo (dois subconjuntos de 5 de um
        # pool de 6 compartilham no maximo 4 elementos) -> precisa dos 6 bilhetes
        assert resultado["quantidade"] == 6
        assert resultado["custo_total"] == 18.00
        assert all(len(jogo) == 5 for jogo in resultado["jogos"])
        # todos os jogos sao distintos
        assert len({tuple(j) for j in resultado["jogos"]}) == 6

    def test_pool_com_dezenas_repetidas_levanta_erro(self):
        with pytest.raises(ValueError, match="repetidas"):
            gerar_fechamento([1, 2, 2, 3, 4], garantia=(4, 4))

    def test_pool_menor_que_5_levanta_erro(self):
        with pytest.raises(ValueError, match="pelo menos"):
            gerar_fechamento([1, 2, 3], garantia=(3, 3))

    def test_pool_maior_que_limite_levanta_erro(self):
        with pytest.raises(ValueError, match="no máximo"):
            gerar_fechamento(list(range(1, 14)), garantia=(5, 5))

    def test_faixa_fora_do_intervalo_levanta_erro(self):
        with pytest.raises(ValueError, match="faixa"):
            gerar_fechamento([1, 2, 3, 4, 5, 6], garantia=(5, 6))

    def test_k_fora_do_intervalo_levanta_erro(self):
        with pytest.raises(ValueError, match="k deve"):
            gerar_fechamento([1, 2, 3, 4, 5, 6], garantia=(2, 4))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd quina && source venv/bin/activate && pytest testes/integracao/test_fechamento.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement**

Create `quina/src/quina/servicos/fechamento.py`:

```python
"""Fechamento/wheeling: cobertura combinatória aproximada (greedy set-cover).

Não é o mínimo matemático ótimo — cobertura exata é NP-difícil para pools
grandes. LIMITE_POOL mantém o espaço de busca tratável.
"""
from __future__ import annotations

import itertools

from quina.dominio.regras import NUMEROS_POR_SORTEIO, custo_aposta

LIMITE_POOL = 12


def gerar_fechamento(pool: list[int], garantia: tuple[int, int]) -> dict:
    k, faixa = garantia
    pool_ordenado = sorted(pool)

    if len(set(pool_ordenado)) != len(pool_ordenado):
        raise ValueError("pool não pode conter dezenas repetidas")
    if len(pool_ordenado) < NUMEROS_POR_SORTEIO:
        raise ValueError(f"pool deve ter pelo menos {NUMEROS_POR_SORTEIO} dezenas")
    if len(pool_ordenado) > LIMITE_POOL:
        raise ValueError(f"pool suporta no máximo {LIMITE_POOL} dezenas (limite de performance)")
    if not (2 <= faixa <= NUMEROS_POR_SORTEIO):
        raise ValueError(f"faixa de garantia deve estar entre 2 e {NUMEROS_POR_SORTEIO}")
    if not (faixa <= k <= len(pool_ordenado)):
        raise ValueError(f"k deve estar entre {faixa} e o tamanho do pool")

    combinacoes_garantia = list(itertools.combinations(pool_ordenado, k))
    combinacoes_bilhete = list(itertools.combinations(pool_ordenado, NUMEROS_POR_SORTEIO))

    nao_cobertas = set(range(len(combinacoes_garantia)))
    jogos_escolhidos: list[list[int]] = []

    while nao_cobertas:
        melhor_bilhete = None
        melhor_cobertura: set[int] = set()
        for bilhete in combinacoes_bilhete:
            bilhete_set = set(bilhete)
            cobertas = {
                i for i in nao_cobertas
                if len(bilhete_set & set(combinacoes_garantia[i])) >= faixa
            }
            if len(cobertas) > len(melhor_cobertura):
                melhor_cobertura = cobertas
                melhor_bilhete = bilhete

        if melhor_bilhete is None or not melhor_cobertura:
            raise ValueError("não foi possível cobrir todas as combinações de garantia com o pool informado")

        jogos_escolhidos.append(list(melhor_bilhete))
        nao_cobertas -= melhor_cobertura

    custo_total = round(len(jogos_escolhidos) * custo_aposta(NUMEROS_POR_SORTEIO), 2)
    return {"jogos": jogos_escolhidos, "quantidade": len(jogos_escolhidos), "custo_total": custo_total}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd quina && source venv/bin/activate && pytest testes/integracao/test_fechamento.py -v`
Expected: PASS (all 7 tests)

- [ ] **Step 5: Commit**

```bash
git add quina/src/quina/servicos/fechamento.py quina/testes/integracao/test_fechamento.py
git commit -m "feat(quina): add greedy wheeling/fechamento game coverage"
```

---

### Task 7: Backtest walk-forward ("treino")

**Files:**
- Create: `quina/src/quina/servicos/backtest.py`
- Test: `quina/testes/integracao/test_backtest.py`

**Interfaces:**
- Consumes: `FAIXAS_ACERTOS`, `NUMEROS_POR_SORTEIO`, `TOTAL_NUMEROS` from `quina.dominio.regras`; `DatabaseManager` from `quina.infra.dados.banco`; `scoring.gerar_candidatos` (Task 4); `gerar_candidato_frequencia_atraso` (Task 5).
- Produces:
  - `ESTRATEGIAS_DISPONIVEIS: tuple[str, ...] = ("filtros", "frequencia_atraso")`
  - `rodar_backtest(estrategia: str, janela: int = 300, draws: list[dict] | None = None, db: DatabaseManager | None = None) -> dict` — `{"janela", "total_rodadas", "taxa_estrategia": {"2":..,"3":..,"4":..,"5":..}, "taxa_baseline": {...}, "tempo_execucao_segundos"}`. Raises `ValueError` for unknown estrategia or `< 2` draws.

- [ ] **Step 1: Write the failing tests**

Create `quina/testes/integracao/test_backtest.py`:

```python
from pathlib import Path

import pytest

from quina.infra.dados.leitor import load_draws
from quina.servicos.backtest import rodar_backtest

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "sample_draws"


def _draws_como_dicts():
    return [
        {"concurso": d.concurso, "data": d.data, "dezenas": d.dezenas}
        for d in load_draws(FIXTURES_DIR)
    ]


class TestRodarBacktest:
    def test_estrutura_do_resultado(self):
        resultado = rodar_backtest(estrategia="frequencia_atraso", janela=5, draws=_draws_como_dicts())

        assert set(resultado.keys()) == {
            "janela", "total_rodadas", "taxa_estrategia", "taxa_baseline", "tempo_execucao_segundos"
        }
        assert resultado["janela"] == 5
        assert resultado["total_rodadas"] == 5
        assert set(resultado["taxa_estrategia"].keys()) == {"2", "3", "4", "5"}
        assert set(resultado["taxa_baseline"].keys()) == {"2", "3", "4", "5"}

    def test_taxas_entre_zero_e_um(self):
        resultado = rodar_backtest(estrategia="frequencia_atraso", janela=5, draws=_draws_como_dicts())

        for taxa in {**resultado["taxa_estrategia"], **resultado["taxa_baseline"]}.values():
            assert 0.0 <= taxa <= 1.0

    def test_janela_maior_que_historico_e_clampada(self):
        draws = _draws_como_dicts()
        resultado = rodar_backtest(estrategia="frequencia_atraso", janela=1000, draws=draws)

        assert resultado["janela"] == len(draws) - 1
        assert resultado["total_rodadas"] == len(draws) - 1

    def test_estrategia_filtros_roda_sem_erro(self):
        resultado = rodar_backtest(estrategia="filtros", janela=3, draws=_draws_como_dicts())
        assert resultado["total_rodadas"] == 3

    def test_estrategia_desconhecida_levanta_erro(self):
        with pytest.raises(ValueError, match="desconhecida"):
            rodar_backtest(estrategia="inexistente", janela=5, draws=_draws_como_dicts())

    def test_dados_insuficientes_levanta_erro(self):
        um_concurso = [{"concurso": 1, "data": "x", "dezenas": [1, 2, 3, 4, 5]}]
        with pytest.raises(ValueError, match="insuficientes"):
            rodar_backtest(estrategia="filtros", janela=5, draws=um_concurso)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd quina && source venv/bin/activate && pytest testes/integracao/test_backtest.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement**

Create `quina/src/quina/servicos/backtest.py`:

```python
"""Backtest walk-forward de estratégias contra o histórico real da Quina."""
from __future__ import annotations

import random
import time
from typing import Optional

from quina.dominio.regras import FAIXAS_ACERTOS, NUMEROS_POR_SORTEIO, TOTAL_NUMEROS
from quina.infra.dados.banco import DatabaseManager
from quina.servicos.estrategias import scoring
from quina.servicos.estrategias.frequencia_atraso import gerar_candidato_frequencia_atraso

ESTRATEGIAS_DISPONIVEIS = ("filtros", "frequencia_atraso")

_CANDIDATOS_POR_RODADA = 100


def _gerar_candidato(estrategia: str, historico: list[dict]) -> list[int]:
    if estrategia == "filtros":
        candidatos = scoring.gerar_candidatos(
            quantidade=_CANDIDATOS_POR_RODADA, tamanho_aposta=NUMEROS_POR_SORTEIO, draws=historico
        )
        return candidatos[0]["dezenas"]
    return gerar_candidato_frequencia_atraso(historico, NUMEROS_POR_SORTEIO)["dezenas"]


def rodar_backtest(
    estrategia: str,
    janela: int = 300,
    draws: Optional[list[dict]] = None,
    db: Optional[DatabaseManager] = None,
) -> dict:
    if estrategia not in ESTRATEGIAS_DISPONIVEIS:
        raise ValueError(f"estratégia desconhecida: {estrategia}")

    todos = draws if draws is not None else (db or DatabaseManager()).get_all_concursos()
    if len(todos) < 2:
        raise ValueError("dados insuficientes para backtest (mínimo 2 concursos)")

    janela_efetiva = min(janela, len(todos) - 1)
    inicio = len(todos) - janela_efetiva

    contagem_estrategia = {f: 0 for f in FAIXAS_ACERTOS}
    contagem_baseline = {f: 0 for f in FAIXAS_ACERTOS}

    inicio_tempo = time.monotonic()
    for i in range(inicio, len(todos)):
        historico = todos[:i]
        resultado_real = set(todos[i]["dezenas"])

        candidato_estrategia = set(_gerar_candidato(estrategia, historico))
        candidato_baseline = set(random.sample(range(1, TOTAL_NUMEROS + 1), NUMEROS_POR_SORTEIO))

        acertos_estrategia = len(candidato_estrategia & resultado_real)
        acertos_baseline = len(candidato_baseline & resultado_real)
        if acertos_estrategia in contagem_estrategia:
            contagem_estrategia[acertos_estrategia] += 1
        if acertos_baseline in contagem_baseline:
            contagem_baseline[acertos_baseline] += 1
    tempo_execucao = round(time.monotonic() - inicio_tempo, 3)

    total_rodadas = len(todos) - inicio
    return {
        "janela": janela_efetiva,
        "total_rodadas": total_rodadas,
        "taxa_estrategia": {str(f): contagem_estrategia[f] / total_rodadas for f in FAIXAS_ACERTOS},
        "taxa_baseline": {str(f): contagem_baseline[f] / total_rodadas for f in FAIXAS_ACERTOS},
        "tempo_execucao_segundos": tempo_execucao,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd quina && source venv/bin/activate && pytest testes/integracao/test_backtest.py -v`
Expected: PASS (all 6 tests)

- [ ] **Step 5: Commit**

```bash
git add quina/src/quina/servicos/backtest.py quina/testes/integracao/test_backtest.py
git commit -m "feat(quina): add walk-forward backtest with random baseline comparison"
```

---

### Task 8: Portfólio por orçamento

**Files:**
- Create: `quina/src/quina/servicos/portfolio.py`
- Test: `quina/testes/integracao/test_portfolio.py`

**Interfaces:**
- Consumes: `custo_aposta` from `quina.dominio.regras` (Task 1); `scoring.gerar_candidatos` (Task 4).
- Produces:
  - `PERFIS_TAMANHOS: dict[str, list[int]] = {"conservador": [5], "equilibrado": [5,6,7,8], "agressivo": [10,12,15]}`
  - `gerar_portfolio(orcamento: float, perfil: str, draws: list[dict]) -> dict` — `{"jogos": list[dict], "custo_total": float, "orcamento_sobra": float}`. Raises `ValueError` for unknown perfil or `orcamento <= 0`.

- [ ] **Step 1: Write the failing tests**

Create `quina/testes/integracao/test_portfolio.py`:

```python
import pytest

from quina.servicos.portfolio import gerar_portfolio


def _draws_fixture():
    return [
        {"concurso": 1, "data": "01/01/2026", "dezenas": [1, 2, 3, 4, 5]},
        {"concurso": 2, "data": "02/01/2026", "dezenas": [6, 7, 8, 9, 10]},
    ]


class TestGerarPortfolio:
    def test_perfil_desconhecido_levanta_erro(self):
        with pytest.raises(ValueError, match="perfil desconhecido"):
            gerar_portfolio(orcamento=100, perfil="inexistente", draws=_draws_fixture())

    def test_orcamento_invalido_levanta_erro(self):
        with pytest.raises(ValueError, match="orçamento"):
            gerar_portfolio(orcamento=0, perfil="conservador", draws=_draws_fixture())

    def test_orcamento_insuficiente_retorna_vazio(self):
        resultado = gerar_portfolio(orcamento=1.0, perfil="conservador", draws=_draws_fixture())

        assert resultado["jogos"] == []
        assert resultado["custo_total"] == 0.0
        assert resultado["orcamento_sobra"] == 1.0

    def test_conservador_gera_apenas_jogos_de_5_dezenas(self):
        resultado = gerar_portfolio(orcamento=30.0, perfil="conservador", draws=_draws_fixture())

        assert all(j["tamanho_aposta"] == 5 for j in resultado["jogos"])
        assert resultado["custo_total"] <= 30.0

    def test_custo_total_mais_sobra_igual_ao_orcamento(self):
        resultado = gerar_portfolio(orcamento=50.0, perfil="equilibrado", draws=_draws_fixture())

        assert resultado["custo_total"] <= 50.0
        assert resultado["custo_total"] + resultado["orcamento_sobra"] == pytest.approx(50.0)

    def test_agressivo_com_orcamento_suficiente_para_exatamente_um_jogo(self):
        resultado = gerar_portfolio(orcamento=1000.0, perfil="agressivo", draws=_draws_fixture())

        # custo_aposta(10)=756.00; custo_aposta(12)=2376.00 e custo_aposta(15)=9009.00
        # excedem 1000, entao so cabe 1 jogo de tamanho 10
        assert len(resultado["jogos"]) == 1
        assert resultado["jogos"][0]["tamanho_aposta"] == 10
        assert resultado["custo_total"] == 756.0
        assert resultado["orcamento_sobra"] == 244.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd quina && source venv/bin/activate && pytest testes/integracao/test_portfolio.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement**

Create `quina/src/quina/servicos/portfolio.py`:

```python
"""Geração de portfólio de jogos que respeita um orçamento informado."""
from __future__ import annotations

from quina.dominio.regras import custo_aposta
from quina.servicos.estrategias import scoring

PERFIS_TAMANHOS = {
    "conservador": [5],
    "equilibrado": [5, 6, 7, 8],
    "agressivo": [10, 12, 15],
}

_CANDIDATOS_POR_TAMANHO = 50


def gerar_portfolio(orcamento: float, perfil: str, draws: list[dict]) -> dict:
    if perfil not in PERFIS_TAMANHOS:
        raise ValueError(f"perfil desconhecido: {perfil}. Use um de: {', '.join(PERFIS_TAMANHOS)}")
    if orcamento <= 0:
        raise ValueError("orçamento deve ser maior que zero")

    candidatos = []
    for tamanho in PERFIS_TAMANHOS[perfil]:
        custo = custo_aposta(tamanho)
        if custo > orcamento:
            continue
        gerados = scoring.gerar_candidatos(quantidade=_CANDIDATOS_POR_TAMANHO, tamanho_aposta=tamanho, draws=draws)
        for candidato in gerados:
            candidatos.append({
                "dezenas": candidato["dezenas"],
                "score": candidato["score"],
                "tamanho_aposta": tamanho,
                "custo": custo,
            })

    candidatos.sort(key=lambda c: c["score"], reverse=True)

    jogos = []
    orcamento_restante = round(orcamento, 2)
    for candidato in candidatos:
        if candidato["custo"] <= orcamento_restante:
            jogos.append(candidato)
            orcamento_restante = round(orcamento_restante - candidato["custo"], 2)

    custo_total = round(orcamento - orcamento_restante, 2)
    return {"jogos": jogos, "custo_total": custo_total, "orcamento_sobra": orcamento_restante}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd quina && source venv/bin/activate && pytest testes/integracao/test_portfolio.py -v`
Expected: PASS (all 6 tests)

- [ ] **Step 5: Commit**

```bash
git add quina/src/quina/servicos/portfolio.py quina/testes/integracao/test_portfolio.py
git commit -m "feat(quina): add budget-based portfolio generation"
```

---

### Task 9: Validação automática de acertos ao sincronizar dados

**Files:**
- Modify: `quina/src/quina/infra/dados/api_caixa.py`
- Test: `quina/testes/integracao/test_api_caixa.py`

**Interfaces:**
- Consumes: `DatabaseManager.atualizar_acertos_pendentes` (Task 2).
- Produces: no new public interface — `QuinaFetcher.sync_new_draws()` now also validates pending `jogos_gerados` for each newly synced concurso. This covers both `quina dados atualizar` (CLI) and `POST /api/atualizar` (Flask), since both call `sync_new_draws()`.

- [ ] **Step 1: Write the failing tests**

Append to `quina/testes/integracao/test_api_caixa.py` (add at the end of the file):

```python
class TestSyncValidaJogosGerados:
    @responses.activate
    def test_sync_atualiza_acertos_de_jogos_pendentes(self, tmp_path):
        db = DatabaseManager(db_path=tmp_path / "test.db")
        db.upsert_concurso(7058, "06/07/2026", [8, 26, 27, 66, 79])
        db.salvar_jogo_gerado(
            estrategia="filtros", tamanho_aposta=5, dezenas=[27, 47, 57, 70, 78],
            score=0.8, custo=3.0, concurso_alvo_validacao=7059,
        )
        responses.add(responses.GET, f"{API_QUINA}/latest", json=RAW_7059, status=200)
        responses.add(responses.GET, f"{API_QUINA}/7059", json=RAW_7059, status=200)
        fetcher = QuinaFetcher(db=db, data_dir=tmp_path)

        fetcher.sync_new_draws()

        jogos = db.listar_jogos_gerados()
        assert jogos[0]["acertos"] == 5  # dezenas do jogo batem 100% com o sorteio 7059

    @responses.activate
    def test_sync_nao_toca_jogos_de_outro_concurso_alvo(self, tmp_path):
        db = DatabaseManager(db_path=tmp_path / "test.db")
        db.upsert_concurso(7058, "06/07/2026", [8, 26, 27, 66, 79])
        db.salvar_jogo_gerado(
            estrategia="filtros", tamanho_aposta=5, dezenas=[1, 2, 3, 4, 5],
            score=0.5, custo=3.0, concurso_alvo_validacao=9999,
        )
        responses.add(responses.GET, f"{API_QUINA}/latest", json=RAW_7059, status=200)
        responses.add(responses.GET, f"{API_QUINA}/7059", json=RAW_7059, status=200)
        fetcher = QuinaFetcher(db=db, data_dir=tmp_path)

        fetcher.sync_new_draws()

        jogos = db.listar_jogos_gerados()
        assert jogos[0]["acertos"] is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd quina && source venv/bin/activate && pytest testes/integracao/test_api_caixa.py::TestSyncValidaJogosGerados -v`
Expected: FAIL — `jogos[0]["acertos"]` is `None` instead of `5` in the first test

- [ ] **Step 3: Implement**

Modify `quina/src/quina/infra/dados/api_caixa.py` inside `sync_new_draws` (currently `quina/src/quina/infra/dados/api_caixa.py:150-156`), adding one line after `self._save_concurso_json(...)`:

```python
        for num in range(start, end + 1):
            rec = self._fetch_concurso_api(num)
            if rec:
                self.db.upsert_concurso(rec["concurso"], rec["data"], rec["dezenas"], rec["raw"])
                self._save_concurso_json(rec["concurso"], rec["raw"])
                self.db.atualizar_acertos_pendentes(rec["concurso"], rec["dezenas"])
                new_count += 1
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd quina && source venv/bin/activate && pytest testes/integracao/test_api_caixa.py -v`
Expected: PASS (all tests, including the existing suite unaffected)

- [ ] **Step 5: Commit**

```bash
git add quina/src/quina/infra/dados/api_caixa.py quina/testes/integracao/test_api_caixa.py
git commit -m "feat(quina): auto-validate pending jogos_gerados hits on data sync"
```

---

### Task 10: CLI `quina modelo` (treinar, leaderboard)

**Files:**
- Create: `quina/src/quina/interface/cli/modelo.py`
- Modify: `quina/src/quina/interface/cli/app.py`
- Test: `quina/testes/integracao/test_cli_modelo.py`

**Interfaces:**
- Consumes: `DatabaseManager` (Task 2), `rodar_backtest`, `ESTRATEGIAS_DISPONIVEIS` (Task 7).
- Produces: `quina modelo treinar [--estrategia TEXT] [--janela INT]`, `quina modelo leaderboard [--limite INT]` CLI commands.

- [ ] **Step 1: Write the failing tests**

Create `quina/testes/integracao/test_cli_modelo.py`:

```python
from functools import partial

from typer.testing import CliRunner

from quina.infra.dados.banco import DatabaseManager
from quina.interface.cli import modelo as modelo_cli

runner = CliRunner()


def _patch_db(monkeypatch, tmp_path):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(modelo_cli, "DatabaseManager", partial(DatabaseManager, db_path=db_path))
    return db_path


def _seed_draws(db):
    for i in range(1, 6):
        db.upsert_concurso(i, f"0{i}/01/2026", [i, i + 10, i + 20, i + 30, i + 40])


class TestTreinarCommand:
    def test_dados_insuficientes(self, monkeypatch, tmp_path):
        _patch_db(monkeypatch, tmp_path)

        result = runner.invoke(modelo_cli.app, ["treinar"])

        assert result.exit_code == 1
        assert "insuficientes" in result.stdout

    def test_treinar_com_dados(self, monkeypatch, tmp_path):
        db_path = _patch_db(monkeypatch, tmp_path)
        _seed_draws(DatabaseManager(db_path=db_path))

        result = runner.invoke(modelo_cli.app, ["treinar", "--estrategia", "frequencia_atraso", "--janela", "3"])

        assert result.exit_code == 0
        assert "Backtest" in result.stdout


class TestLeaderboardCommand:
    def test_sem_backtests(self, monkeypatch, tmp_path):
        _patch_db(monkeypatch, tmp_path)

        result = runner.invoke(modelo_cli.app, ["leaderboard"])

        assert result.exit_code == 0
        assert "Nenhum backtest" in result.stdout

    def test_com_backtests(self, monkeypatch, tmp_path):
        db_path = _patch_db(monkeypatch, tmp_path)
        db = DatabaseManager(db_path=db_path)
        db.salvar_backtest("filtros", 100, {
            "taxa_estrategia": {"2": 0.1, "3": 0.0, "4": 0.0, "5": 0.0},
            "taxa_baseline": {"2": 0.1, "3": 0.0, "4": 0.0, "5": 0.0},
        })

        result = runner.invoke(modelo_cli.app, ["leaderboard"])

        assert result.exit_code == 0
        assert "filtros" in result.stdout
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd quina && source venv/bin/activate && pytest testes/integracao/test_cli_modelo.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'quina.interface.cli.modelo'`

- [ ] **Step 3: Implement**

Create `quina/src/quina/interface/cli/modelo.py`:

```python
"""modelo subcommands — backtest de estratégias e leaderboard."""
from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from quina.infra.dados.banco import DatabaseManager
from quina.servicos.backtest import ESTRATEGIAS_DISPONIVEIS, rodar_backtest

app = typer.Typer(help="Backtest de estratégias e leaderboard.")
console = Console()


@app.command()
def treinar(
    estrategia: str = typer.Option("filtros", "--estrategia", help=f"Uma de: {', '.join(ESTRATEGIAS_DISPONIVEIS)}"),
    janela: int = typer.Option(300, "--janela", help="Quantidade de concursos recentes usados no backtest"),
) -> None:
    """Roda backtest walk-forward da estratégia e salva no leaderboard."""
    db = DatabaseManager()
    if db.count_concursos() < 2:
        console.print("[red]Dados insuficientes. Execute: quina dados atualizar[/red]")
        raise typer.Exit(1)

    console.print(f"[cyan]Rodando backtest: estratégia={estrategia}, janela={janela}...[/cyan]")
    metricas = rodar_backtest(estrategia=estrategia, janela=janela, db=db)
    db.salvar_backtest(estrategia, metricas["janela"], metricas)

    table = Table(title=f"Backtest — {estrategia}")
    table.add_column("Faixa")
    table.add_column("Taxa estratégia")
    table.add_column("Taxa baseline (aleatório)")
    for faixa in ["2", "3", "4", "5"]:
        table.add_row(
            faixa,
            f"{metricas['taxa_estrategia'][faixa]:.4f}",
            f"{metricas['taxa_baseline'][faixa]:.4f}",
        )
    console.print(table)
    console.print(f"[dim]{metricas['total_rodadas']} rodadas em {metricas['tempo_execucao_segundos']}s[/dim]")


@app.command()
def leaderboard(limite: int = typer.Option(20, "--limite")) -> None:
    """Lista os últimos backtests salvos."""
    db = DatabaseManager()
    registros = db.listar_backtests(limite=limite)
    if not registros:
        console.print("[yellow]Nenhum backtest encontrado. Execute: quina modelo treinar[/yellow]")
        raise typer.Exit(0)

    table = Table(title="Leaderboard de estratégias")
    table.add_column("ID")
    table.add_column("Estratégia")
    table.add_column("Janela")
    table.add_column("Taxa 5 acertos")
    table.add_column("Criado em")
    for r in registros:
        table.add_row(
            str(r["id"]), r["estrategia"], str(r["janela"]),
            f"{r['metricas']['taxa_estrategia']['5']:.4f}", r["criado_em"],
        )
    console.print(table)
```

Modify `quina/src/quina/interface/cli/app.py` (currently 27 lines) to register the new sub-app:

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
from quina.interface.cli.modelo import app as modelo_app

app = typer.Typer(
    name="quina",
    help="Sistema de previsão Quina — dados, modelos, portfólio e experimentos.",
    add_completion=False,
)
console = Console()

app.add_typer(dados_app, name="dados")
app.add_typer(modelo_app, name="modelo")


if __name__ == "__main__":
    app()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd quina && source venv/bin/activate && pytest testes/integracao/test_cli_modelo.py -v`
Expected: PASS (all 4 tests)

- [ ] **Step 5: Commit**

```bash
git add quina/src/quina/interface/cli/modelo.py quina/src/quina/interface/cli/app.py quina/testes/integracao/test_cli_modelo.py
git commit -m "feat(quina): add 'quina modelo treinar/leaderboard' CLI commands"
```

---

### Task 11: CLI `quina jogos` (gerar, fechamento)

**Files:**
- Create: `quina/src/quina/interface/cli/jogos.py`
- Modify: `quina/src/quina/interface/cli/app.py`
- Test: `quina/testes/integracao/test_cli_jogos.py`

**Interfaces:**
- Consumes: `custo_aposta` (Task 1), `DatabaseManager` (Task 2), `scoring.gerar_candidatos`/`top_k` (Task 4), `gerar_candidato_frequencia_atraso` (Task 5), `gerar_fechamento` (Task 6).
- Produces: `quina jogos gerar [--estrategia TEXT] [--tamanho INT] [--n INT] [--concurso-alvo INT]`, `quina jogos fechamento --dezenas TEXT --garantia TEXT` CLI commands.

- [ ] **Step 1: Write the failing tests**

Create `quina/testes/integracao/test_cli_jogos.py`:

```python
from functools import partial

from typer.testing import CliRunner

from quina.infra.dados.banco import DatabaseManager
from quina.interface.cli import jogos as jogos_cli

runner = CliRunner()


def _patch_db(monkeypatch, tmp_path):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(jogos_cli, "DatabaseManager", partial(DatabaseManager, db_path=db_path))
    return db_path


def _seed_draws(db):
    for i in range(1, 6):
        db.upsert_concurso(i, f"0{i}/01/2026", [i, i + 10, i + 20, i + 30, i + 40])


class TestGerarCommand:
    def test_dados_insuficientes(self, monkeypatch, tmp_path):
        _patch_db(monkeypatch, tmp_path)

        result = runner.invoke(jogos_cli.app, ["gerar"])

        assert result.exit_code == 1

    def test_gerar_com_filtros(self, monkeypatch, tmp_path):
        db_path = _patch_db(monkeypatch, tmp_path)
        _seed_draws(DatabaseManager(db_path=db_path))

        result = runner.invoke(jogos_cli.app, ["gerar", "--estrategia", "filtros", "--tamanho", "5", "--n", "3"])

        assert result.exit_code == 0
        assert "Custo total" in result.stdout

    def test_gerar_persiste_no_banco(self, monkeypatch, tmp_path):
        db_path = _patch_db(monkeypatch, tmp_path)
        db = DatabaseManager(db_path=db_path)
        _seed_draws(db)

        runner.invoke(jogos_cli.app, ["gerar", "--estrategia", "filtros", "--tamanho", "5", "--n", "3"])

        assert len(db.listar_jogos_gerados()) == 3


class TestFechamentoCommand:
    def test_fechamento_valido(self, monkeypatch, tmp_path):
        _patch_db(monkeypatch, tmp_path)

        result = runner.invoke(jogos_cli.app, ["fechamento", "--dezenas", "1,2,3,4,5", "--garantia", "5,5"])

        assert result.exit_code == 0
        assert "custo total" in result.stdout.lower()

    def test_fechamento_invalido(self, monkeypatch, tmp_path):
        _patch_db(monkeypatch, tmp_path)

        result = runner.invoke(jogos_cli.app, ["fechamento", "--dezenas", "1,2,3", "--garantia", "3,3"])

        assert result.exit_code != 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd quina && source venv/bin/activate && pytest testes/integracao/test_cli_jogos.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'quina.interface.cli.jogos'`

- [ ] **Step 3: Implement**

Create `quina/src/quina/interface/cli/jogos.py`:

```python
"""jogos subcommands — geração de jogos e fechamento."""
from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from quina.dominio.regras import custo_aposta
from quina.infra.dados.banco import DatabaseManager
from quina.servicos import fechamento as fechamento_servico
from quina.servicos.estrategias import scoring
from quina.servicos.estrategias.frequencia_atraso import gerar_candidato_frequencia_atraso

app = typer.Typer(help="Geração de jogos: filtros/frequência+atraso e fechamento.")
console = Console()


@app.command()
def gerar(
    estrategia: str = typer.Option("filtros", "--estrategia"),
    tamanho: int = typer.Option(5, "--tamanho", help="Tamanho da aposta (5-15)"),
    n: int = typer.Option(5, "--n", help="Quantidade de jogos a gerar"),
    concurso_alvo: int = typer.Option(None, "--concurso-alvo", help="Concurso a validar depois (opcional)"),
) -> None:
    """Gera N jogos com a estratégia escolhida e persiste no banco."""
    db = DatabaseManager()
    draws = db.get_all_concursos()
    if len(draws) < 2:
        console.print("[red]Dados insuficientes. Execute: quina dados atualizar[/red]")
        raise typer.Exit(1)

    if estrategia == "filtros":
        candidatos = scoring.gerar_candidatos(quantidade=max(200, n * 20), tamanho_aposta=tamanho, draws=draws)
        selecionados = scoring.top_k(candidatos, n)
    elif estrategia == "frequencia_atraso":
        selecionados = [gerar_candidato_frequencia_atraso(draws, tamanho) for _ in range(n)]
    else:
        console.print(f"[red]Estratégia desconhecida: {estrategia}[/red]")
        raise typer.Exit(1)

    custo_unitario = custo_aposta(tamanho)
    table = Table(title=f"Jogos gerados — {estrategia}")
    table.add_column("Dezenas")
    table.add_column("Score")
    for jogo in selecionados:
        db.salvar_jogo_gerado(
            estrategia=estrategia, tamanho_aposta=tamanho, dezenas=jogo["dezenas"],
            score=jogo.get("score"), custo=custo_unitario, concurso_alvo_validacao=concurso_alvo,
        )
        table.add_row("  ".join(f"{d:02d}" for d in jogo["dezenas"]), f"{jogo.get('score', 0):.3f}")
    console.print(table)
    console.print(f"[dim]Custo total: R$ {custo_unitario * n:.2f}[/dim]")


@app.command()
def fechamento(
    dezenas: str = typer.Option(..., "--dezenas", help="Pool de dezenas separadas por vírgula, ex: 1,5,12,20,33,47"),
    garantia: str = typer.Option(..., "--garantia", help="k,faixa — ex: 4,4 garante quadra se 4 do pool saírem"),
) -> None:
    """Gera cobertura de fechamento (greedy) para o pool e garantia informados."""
    pool = [int(d.strip()) for d in dezenas.split(",")]
    k_str, faixa_str = garantia.split(",")
    resultado = fechamento_servico.gerar_fechamento(pool, (int(k_str), int(faixa_str)))

    table = Table(title="Fechamento")
    table.add_column("Jogo")
    for jogo in resultado["jogos"]:
        table.add_row("  ".join(f"{d:02d}" for d in jogo))
    console.print(table)
    console.print(f"[dim]{resultado['quantidade']} jogos — custo total R$ {resultado['custo_total']:.2f}[/dim]")
```

Modify `quina/src/quina/interface/cli/app.py` to add:

```python
from quina.interface.cli.jogos import app as jogos_app
```

and, after `app.add_typer(modelo_app, name="modelo")`:

```python
app.add_typer(jogos_app, name="jogos")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd quina && source venv/bin/activate && pytest testes/integracao/test_cli_jogos.py -v`
Expected: PASS (all 5 tests). Note `fechamento` with an invalid pool raises `ValueError` inside the command with no `typer.Exit`/try-except wrapper — Typer/Click will surface this as a non-zero exit with the traceback in `result.output`, which satisfies `test_fechamento_invalido`'s `exit_code != 0` check.

- [ ] **Step 5: Commit**

```bash
git add quina/src/quina/interface/cli/jogos.py quina/src/quina/interface/cli/app.py quina/testes/integracao/test_cli_jogos.py
git commit -m "feat(quina): add 'quina jogos gerar/fechamento' CLI commands"
```

---

### Task 12: CLI `quina portfolio` (gerar)

**Files:**
- Create: `quina/src/quina/interface/cli/portfolio.py`
- Modify: `quina/src/quina/interface/cli/app.py`
- Test: `quina/testes/integracao/test_cli_portfolio.py`

**Interfaces:**
- Consumes: `DatabaseManager` (Task 2), `gerar_portfolio`/`PERFIS_TAMANHOS` (Task 8).
- Produces: `quina portfolio gerar --orcamento FLOAT [--perfil TEXT]` CLI command.

- [ ] **Step 1: Write the failing tests**

Create `quina/testes/integracao/test_cli_portfolio.py`:

```python
from functools import partial

from typer.testing import CliRunner

from quina.infra.dados.banco import DatabaseManager
from quina.interface.cli import portfolio as portfolio_cli

runner = CliRunner()


def _patch_db(monkeypatch, tmp_path):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(portfolio_cli, "DatabaseManager", partial(DatabaseManager, db_path=db_path))
    return db_path


def _seed_draws(db):
    for i in range(1, 6):
        db.upsert_concurso(i, f"0{i}/01/2026", [i, i + 10, i + 20, i + 30, i + 40])


class TestGerarCommand:
    def test_dados_insuficientes(self, monkeypatch, tmp_path):
        _patch_db(monkeypatch, tmp_path)

        result = runner.invoke(portfolio_cli.app, ["gerar", "--orcamento", "30"])

        assert result.exit_code == 1

    def test_gerar_com_dados(self, monkeypatch, tmp_path):
        db_path = _patch_db(monkeypatch, tmp_path)
        _seed_draws(DatabaseManager(db_path=db_path))

        result = runner.invoke(portfolio_cli.app, ["gerar", "--orcamento", "30", "--perfil", "conservador"])

        assert result.exit_code == 0
        assert "Custo total" in result.stdout
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd quina && source venv/bin/activate && pytest testes/integracao/test_cli_portfolio.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'quina.interface.cli.portfolio'`

- [ ] **Step 3: Implement**

Create `quina/src/quina/interface/cli/portfolio.py`:

```python
"""portfolio subcommand — geração de portfólio de jogos por orçamento."""
from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from quina.infra.dados.banco import DatabaseManager
from quina.servicos.portfolio import PERFIS_TAMANHOS, gerar_portfolio

app = typer.Typer(help="Geração de portfólio de jogos por orçamento.")
console = Console()


@app.command()
def gerar(
    orcamento: float = typer.Option(..., "--orcamento"),
    perfil: str = typer.Option("equilibrado", "--perfil", help=f"Um de: {', '.join(PERFIS_TAMANHOS)}"),
) -> None:
    """Gera um portfólio de jogos que respeita o orçamento informado."""
    db = DatabaseManager()
    draws = db.get_all_concursos()
    if len(draws) < 2:
        console.print("[red]Dados insuficientes. Execute: quina dados atualizar[/red]")
        raise typer.Exit(1)

    resultado = gerar_portfolio(orcamento=orcamento, perfil=perfil, draws=draws)

    table = Table(title=f"Portfólio — {perfil}")
    table.add_column("Dezenas")
    table.add_column("Tamanho")
    table.add_column("Custo")
    for jogo in resultado["jogos"]:
        table.add_row(
            "  ".join(f"{d:02d}" for d in jogo["dezenas"]),
            str(jogo["tamanho_aposta"]),
            f"R$ {jogo['custo']:.2f}",
        )
    console.print(table)
    console.print(
        f"[dim]Custo total: R$ {resultado['custo_total']:.2f} — "
        f"sobra: R$ {resultado['orcamento_sobra']:.2f}[/dim]"
    )
```

Modify `quina/src/quina/interface/cli/app.py` to add:

```python
from quina.interface.cli.portfolio import app as portfolio_app
```

and, after `app.add_typer(jogos_app, name="jogos")`:

```python
app.add_typer(portfolio_app, name="portfolio")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd quina && source venv/bin/activate && pytest testes/integracao/test_cli_portfolio.py -v`
Expected: PASS (both tests)

- [ ] **Step 5: Commit**

```bash
git add quina/src/quina/interface/cli/portfolio.py quina/src/quina/interface/cli/app.py quina/testes/integracao/test_cli_portfolio.py
git commit -m "feat(quina): add 'quina portfolio gerar' CLI command"
```

---

### Task 13: Rotas Flask (treinos, jogos, fechamento, portfolio)

**Files:**
- Modify: `quina/src/quina/interface/painel/server.py`
- Test: `quina/testes/integracao/test_server_estrategias.py`

**Interfaces:**
- Consumes: everything from Tasks 1–8.
- Produces: `POST /api/treinos/iniciar`, `GET /api/treinos`, `POST /api/jogos/gerar`, `GET /api/jogos`, `POST /api/fechamento`, `POST /api/portfolio`.

- [ ] **Step 1: Write the failing tests**

Create `quina/testes/integracao/test_server_estrategias.py`:

```python
"""Tests for the new Quina dashboard routes: treinos, jogos, fechamento, portfolio."""
from functools import partial

import pytest

from quina.infra.dados.banco import DatabaseManager
from quina.interface.painel import server as painel_server


def _patch_db(monkeypatch, tmp_path):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(painel_server, "DatabaseManager", partial(DatabaseManager, db_path=db_path))
    return db_path


@pytest.fixture
def client():
    painel_server.app.config["TESTING"] = True
    return painel_server.app.test_client()


def _seed_draws(db):
    db.upsert_concurso(1, "01/01/2026", [1, 2, 3, 4, 5])
    db.upsert_concurso(2, "02/01/2026", [6, 7, 8, 9, 10])
    db.upsert_concurso(3, "03/01/2026", [11, 12, 13, 14, 15])


class TestApiTreinos:
    def test_iniciar_dados_insuficientes(self, client, monkeypatch, tmp_path):
        _patch_db(monkeypatch, tmp_path)

        resp = client.post("/api/treinos/iniciar", json={"estrategia": "filtros", "janela": 5})

        assert resp.status_code == 400

    def test_iniciar_com_dados(self, client, monkeypatch, tmp_path):
        db_path = _patch_db(monkeypatch, tmp_path)
        _seed_draws(DatabaseManager(db_path=db_path))

        resp = client.post("/api/treinos/iniciar", json={"estrategia": "frequencia_atraso", "janela": 2})
        data = resp.get_json()

        assert resp.status_code == 200
        assert "job_id" in data
        assert data["resultado"]["total_rodadas"] == 2

    def test_iniciar_estrategia_invalida(self, client, monkeypatch, tmp_path):
        db_path = _patch_db(monkeypatch, tmp_path)
        _seed_draws(DatabaseManager(db_path=db_path))

        resp = client.post("/api/treinos/iniciar", json={"estrategia": "inexistente"})

        assert resp.status_code == 400

    def test_listar(self, client, monkeypatch, tmp_path):
        db_path = _patch_db(monkeypatch, tmp_path)
        db = DatabaseManager(db_path=db_path)
        db.salvar_backtest("filtros", 100, {"x": 1})

        resp = client.get("/api/treinos")
        data = resp.get_json()

        assert resp.status_code == 200
        assert len(data["backtests"]) == 1


class TestApiJogos:
    def test_gerar_dados_insuficientes(self, client, monkeypatch, tmp_path):
        _patch_db(monkeypatch, tmp_path)

        resp = client.post("/api/jogos/gerar", json={"estrategia": "filtros", "tamanho_aposta": 5, "quantidade": 3})

        assert resp.status_code == 400

    def test_gerar_com_dados(self, client, monkeypatch, tmp_path):
        db_path = _patch_db(monkeypatch, tmp_path)
        _seed_draws(DatabaseManager(db_path=db_path))

        resp = client.post("/api/jogos/gerar", json={"estrategia": "filtros", "tamanho_aposta": 5, "quantidade": 3})
        data = resp.get_json()

        assert resp.status_code == 200
        assert len(data["jogos"]) == 3
        assert all(len(j["dezenas"]) == 5 for j in data["jogos"])

    def test_listar(self, client, monkeypatch, tmp_path):
        db_path = _patch_db(monkeypatch, tmp_path)
        db = DatabaseManager(db_path=db_path)
        db.salvar_jogo_gerado(estrategia="filtros", tamanho_aposta=5, dezenas=[1, 2, 3, 4, 5], score=0.5, custo=3.0)

        resp = client.get("/api/jogos")
        data = resp.get_json()

        assert resp.status_code == 200
        assert len(data["jogos"]) == 1


class TestApiFechamento:
    def test_fechamento_valido(self, client):
        resp = client.post("/api/fechamento", json={"dezenas": [1, 2, 3, 4, 5], "k": 5, "faixa": 5})
        data = resp.get_json()

        assert resp.status_code == 200
        assert data["quantidade"] == 1
        assert data["custo_total"] == 3.0

    def test_fechamento_pool_invalido(self, client):
        resp = client.post("/api/fechamento", json={"dezenas": [1, 2, 3], "k": 3, "faixa": 3})

        assert resp.status_code == 400


class TestApiPortfolio:
    def test_portfolio_dados_insuficientes(self, client, monkeypatch, tmp_path):
        _patch_db(monkeypatch, tmp_path)

        resp = client.post("/api/portfolio", json={"orcamento": 100, "perfil": "conservador"})

        assert resp.status_code == 400

    def test_portfolio_com_dados(self, client, monkeypatch, tmp_path):
        db_path = _patch_db(monkeypatch, tmp_path)
        _seed_draws(DatabaseManager(db_path=db_path))

        resp = client.post("/api/portfolio", json={"orcamento": 30, "perfil": "conservador"})
        data = resp.get_json()

        assert resp.status_code == 200
        assert data["custo_total"] <= 30
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd quina && source venv/bin/activate && pytest testes/integracao/test_server_estrategias.py -v`
Expected: FAIL with `404 NOT FOUND` on all routes (they don't exist yet)

- [ ] **Step 3: Implement**

Modify `quina/src/quina/interface/painel/server.py`. Change the imports at the top of the file (currently lines 1–10) to:

```python
"""Flask dashboard for Quina — minimal data-only view."""
from __future__ import annotations

import uuid
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from quina.dominio.regras import TOTAL_NUMEROS, custo_aposta
from quina.infra.dados.api_caixa import QuinaFetcher
from quina.infra.dados.banco import DatabaseManager
from quina.servicos import fechamento as fechamento_servico
from quina.servicos import portfolio as portfolio_servico
from quina.servicos.backtest import ESTRATEGIAS_DISPONIVEIS, rodar_backtest
from quina.servicos.estrategias import scoring
from quina.servicos.estrategias.frequencia_atraso import gerar_candidato_frequencia_atraso
```

Append these routes at the end of `quina/src/quina/interface/painel/server.py` (after the existing `api_atualizar` function):

```python
@app.route("/api/treinos/iniciar", methods=["POST"])
def api_treinos_iniciar():
    body = request.get_json(force=True, silent=True) or {}
    estrategia = body.get("estrategia", "filtros")
    janela = int(body.get("janela", 300))

    if estrategia not in ESTRATEGIAS_DISPONIVEIS:
        return jsonify({"error": f"estratégia desconhecida: {estrategia}"}), 400

    db = DatabaseManager()
    if db.count_concursos() < 2:
        return jsonify({"error": "dados insuficientes"}), 400

    metricas = rodar_backtest(estrategia=estrategia, janela=janela, db=db)
    db.salvar_backtest(estrategia, metricas["janela"], metricas)
    return jsonify({"job_id": str(uuid.uuid4()), "resultado": metricas})


@app.route("/api/treinos")
def api_treinos_listar():
    db = DatabaseManager()
    return jsonify({"backtests": db.listar_backtests()})


@app.route("/api/jogos/gerar", methods=["POST"])
def api_jogos_gerar():
    body = request.get_json(force=True, silent=True) or {}
    estrategia = body.get("estrategia", "filtros")
    tamanho = int(body.get("tamanho_aposta", 5))
    quantidade = int(body.get("quantidade", 5))
    concurso_alvo = body.get("concurso_alvo")

    db = DatabaseManager()
    draws = db.get_all_concursos()
    if len(draws) < 2:
        return jsonify({"error": "dados insuficientes"}), 400

    try:
        custo_unitario = custo_aposta(tamanho)
        if estrategia == "filtros":
            candidatos = scoring.gerar_candidatos(
                quantidade=max(200, quantidade * 20), tamanho_aposta=tamanho, draws=draws
            )
            selecionados = scoring.top_k(candidatos, quantidade)
        elif estrategia == "frequencia_atraso":
            selecionados = [gerar_candidato_frequencia_atraso(draws, tamanho) for _ in range(quantidade)]
        else:
            return jsonify({"error": f"estratégia desconhecida: {estrategia}"}), 400
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    jogos = []
    for jogo in selecionados:
        jogo_id = db.salvar_jogo_gerado(
            estrategia=estrategia, tamanho_aposta=tamanho, dezenas=jogo["dezenas"],
            score=jogo.get("score"), custo=custo_unitario, concurso_alvo_validacao=concurso_alvo,
        )
        jogos.append({"id": jogo_id, "dezenas": jogo["dezenas"], "score": jogo.get("score"), "custo": custo_unitario})

    return jsonify({"job_id": str(uuid.uuid4()), "jogos": jogos})


@app.route("/api/jogos")
def api_jogos_listar():
    limite = int(request.args.get("limite", 50))
    offset = int(request.args.get("offset", 0))
    db = DatabaseManager()
    return jsonify({"jogos": db.listar_jogos_gerados(limite=limite, offset=offset)})


@app.route("/api/fechamento", methods=["POST"])
def api_fechamento():
    body = request.get_json(force=True, silent=True) or {}
    pool = body.get("dezenas", [])
    k = body.get("k")
    faixa = body.get("faixa")
    try:
        resultado = fechamento_servico.gerar_fechamento(pool, (int(k), int(faixa)))
        return jsonify(resultado)
    except (ValueError, TypeError) as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/portfolio", methods=["POST"])
def api_portfolio():
    body = request.get_json(force=True, silent=True) or {}
    orcamento = body.get("orcamento")
    perfil = body.get("perfil", "equilibrado")

    db = DatabaseManager()
    draws = db.get_all_concursos()
    if len(draws) < 2:
        return jsonify({"error": "dados insuficientes"}), 400

    try:
        resultado = portfolio_servico.gerar_portfolio(orcamento=float(orcamento), perfil=perfil, draws=draws)
        return jsonify(resultado)
    except (ValueError, TypeError) as exc:
        return jsonify({"error": str(exc)}), 400
```

Note: `TOTAL_NUMEROS` is imported but was already unused before this change too — check whether it's used elsewhere in the file (it is, by `api_frequencia`/`api_atraso`, which import it via `from quina.dominio.regras import TOTAL_NUMEROS` already). Do not duplicate the import; merge `custo_aposta` into the existing `from quina.dominio.regras import TOTAL_NUMEROS` line instead of adding a second one.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd quina && source venv/bin/activate && pytest testes/integracao/test_server_estrategias.py testes/integracao/test_server.py -v`
Expected: PASS (all new tests, existing `test_server.py` suite unaffected)

- [ ] **Step 5: Commit**

```bash
git add quina/src/quina/interface/painel/server.py quina/testes/integracao/test_server_estrategias.py
git commit -m "feat(quina): add Flask routes for treinos, jogos, fechamento, portfolio"
```

---

## Final Verification

After all 13 tasks:

```bash
cd quina && source venv/bin/activate && pytest -v
```

Expected: full suite passes (existing tests + ~70 new tests across the 13 tasks). This closes out the backend sub-project — the dashboard UI that exposes these commands and routes visually is the next sub-project, with its own spec and plan.
