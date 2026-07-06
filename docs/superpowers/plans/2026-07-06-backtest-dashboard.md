# Backtesting de Modelos via Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a user pick one or more lab neural configs, a concurso range, and a retrain cadence in the Lotofácil dashboard, run a leak-free walk-forward backtest (train on N, predict N+1) as a background job, and see per-concurso hits, mean hits, an 11–15 hit distribution, and a model-vs-model-vs-baseline comparison — with results persisted and revisitable.

**Architecture:** A thin service (`rodar_backtest_lab.py`) validates dashboard input and delegates to the existing, unmodified `ExperimentRunner`/`walk_forward` walk-forward engine. A new Typer CLI command runs that service and writes a JSON result file, printing a marker line the dashboard's existing generic subprocess runner (`_run_command`) already knows how to capture. A new SQLite table (`backtests`, on the existing `TreinoRegistry`) tracks job status; new Flask routes start/list/fetch/delete backtests, reusing the existing generic `/api/jobs/<id>/poll` and `/api/jobs/<id>/cancel` routes untouched. A new "Backtest" sidebar tab in `dashboard.html` provides the form, a progress modal, results (table + canvas chart + histogram), and a history list.

**Tech Stack:** Python 3.12, Flask, SQLite (stdlib `sqlite3`), Typer/Rich CLI, pytest, vanilla JS + `<canvas>` (no framework, no build step — matches the rest of `dashboard.html`).

## Global Constraints

- Only the 4 known lab neural config signatures are selectable: `base+temp+priors`, `base+temp+priors+lua`, `base+temp+priors+clima`, `base+temp+priors+lua+clima`. Classic models (`infra/modelos/*`) are out of scope.
- `ExperimentRunner`/`walk_forward` are reused unmodified — no changes to `experimentos/evaluation/walkforward.py` or `experimentos/experiments/runner.py`.
- Baselines (`random`, `frequency`) are always included in every backtest run — this is `ExperimentRunner`'s existing default behavior; nothing to implement for it.
- `retrain_every` is user-configurable (default 50, matching `BACKTEST_RETRAIN_EVERY`).
- Backtest runs execute as background subprocess jobs (same pattern as model training) — never block the Flask request thread.
- Results are persisted (new `backtests` SQLite table + JSON result files under `saida/backtests/`), revisitable without re-running.
- No new frontend test tooling exists in this repo (no Jest/Playwright) — frontend tasks are verified manually in a running dashboard, matching how the rest of `dashboard.html` has always been validated.
- No CLI test tooling (`CliRunner`) currently exists in this repo either; Task 3 introduces it narrowly for the one new command, using mocks — this is a new-but-consistent pattern, not a rewrite of testing conventions elsewhere.

---

## Task 1: `rodar_backtest_lab` service

**Files:**
- Create: `lotofacil/src/lotofacil/servicos/rodar_backtest_lab.py`
- Test: `lotofacil/testes/unidade/servicos/test_rodar_backtest_lab.py`

**Interfaces:**
- Produces: `CONFIGS_CONHECIDAS: tuple[str, ...]` (the 4 allowed signatures), `ResultadoBacktestLab` dataclass (`report: dict`, `warnings: list[str]`), and `rodar_backtest_lab(configs: list[str], start_concurso: int, end_concurso: int, retrain_every: int = BACKTEST_RETRAIN_EVERY) -> ResultadoBacktestLab`. Raises `ValueError` for any invalid input (empty configs, unknown config, `start >= end`, `end` beyond available data, insufficient history). `report` is exactly `ExperimentRunner.run()`'s return dict (`{"results": [...], ...}`), where each `results[i]` entry has `name`, `n_evaluated`, `mean_hits`, `roi_pct`, `sharpe`, `max_drawdown`, `p_value_vs_random`, `rate_ge_11`, `rate_ge_13`, `hits_distribution` (dict keyed by string hit count after JSON round-trip), `equity_curve`, `raw_results` (list of `{concurso, predicted, actual, hits}`).

- [ ] **Step 1: Write the failing test file**

```python
"""Tests for rodar_backtest_lab — leak-free walk-forward backtest wiring."""
import pytest

from lotofacil.dominio.entidades import Sorteio as Draw


def _draw(concurso: int) -> Draw:
    offset = concurso % 25
    dezenas = sorted(((offset + i) % 25) + 1 for i in range(15))
    return Draw(concurso=concurso, data="01/01/2020", dezenas=dezenas)


class _FakeNeuralModel:
    calls: list[list[int]] = []

    def __init__(self, cfg):
        self.cfg = cfg

    def fit(self, draws):
        _FakeNeuralModel.calls.append([d.concurso for d in draws])

    def predict(self, draws):
        return list(range(1, 16))

    @property
    def name(self):
        return "fake_neural"


@pytest.fixture(autouse=True)
def _reset_fake_calls():
    _FakeNeuralModel.calls = []
    yield


def test_rodar_backtest_lab_no_leakage(monkeypatch):
    from lotofacil.servicos import rodar_backtest_lab as module

    draws = [_draw(c) for c in range(1, 351)]
    monkeypatch.setattr(module, "load_draws", lambda: draws)
    monkeypatch.setattr(
        "lotofacil.experimentos.experiments.runner.NeuralModular", _FakeNeuralModel
    )

    resultado = module.rodar_backtest_lab(
        configs=["base+temp+priors"],
        start_concurso=340,
        end_concurso=350,
        retrain_every=1,
    )

    assert resultado.warnings == []
    assert _FakeNeuralModel.calls, "modelo fake nunca foi treinado"
    for k, call_concursos in enumerate(_FakeNeuralModel.calls):
        test_concurso = 340 + k
        assert max(call_concursos) < test_concurso, (
            f"vazamento: treino do passo {k} viu concurso {max(call_concursos)} "
            f"ao prever o concurso {test_concurso}"
        )

    entry = next(
        e for e in resultado.report["results"] if e["name"] == "neural_base+temp+priors"
    )
    assert entry["n_evaluated"] == 11
    assert "error" not in entry


def test_rodar_backtest_lab_shifts_start_when_history_insufficient(monkeypatch):
    from lotofacil.servicos import rodar_backtest_lab as module

    draws = [_draw(c) for c in range(1, 351)]
    monkeypatch.setattr(module, "load_draws", lambda: draws)
    monkeypatch.setattr(
        "lotofacil.experimentos.experiments.runner.NeuralModular", _FakeNeuralModel
    )

    resultado = module.rodar_backtest_lab(
        configs=["base+temp+priors"],
        start_concurso=5,
        end_concurso=310,
        retrain_every=50,
    )

    assert resultado.warnings
    assert "301" in resultado.warnings[0]


def test_rejects_empty_configs():
    from lotofacil.servicos.rodar_backtest_lab import rodar_backtest_lab

    with pytest.raises(ValueError, match="ao menos uma config"):
        rodar_backtest_lab([], 100, 200)


def test_rejects_start_not_less_than_end():
    from lotofacil.servicos.rodar_backtest_lab import rodar_backtest_lab

    with pytest.raises(ValueError, match="menor que"):
        rodar_backtest_lab(["base+temp+priors"], 200, 100)


def test_rejects_unknown_config_signature(monkeypatch):
    from lotofacil.servicos import rodar_backtest_lab as module

    with pytest.raises(ValueError, match="inválid"):
        module.rodar_backtest_lab(["nao_existe"], 100, 200)


def test_rejects_end_beyond_available_data(monkeypatch):
    from lotofacil.servicos import rodar_backtest_lab as module

    draws = [_draw(c) for c in range(1, 351)]
    monkeypatch.setattr(module, "load_draws", lambda: draws)

    with pytest.raises(ValueError, match="último concurso disponível"):
        module.rodar_backtest_lab(["base+temp+priors"], 340, 9999)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd lotofacil && pytest testes/unidade/servicos/test_rodar_backtest_lab.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'lotofacil.servicos.rodar_backtest_lab'`

- [ ] **Step 3: Write the implementation**

```python
"""Backtest walk-forward de modelos neurais do lab, sem vazamento de dados.

Camada fina sobre ExperimentRunner: valida entradas vindas do dashboard,
traduz o intervalo de concursos escolhido pelo usuário para os parâmetros
que ExperimentRunner já entende (period_start/period_end/n_test) e devolve
o relatório pronto para exibição (comparação entre modelos + baselines).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from lotofacil.experimentos.config import BACKTEST_MIN_TRAIN, BACKTEST_RETRAIN_EVERY
from lotofacil.experimentos.data.draws_loader import load_draws
from lotofacil.experimentos.data.feature_flags import FeatureConfig
from lotofacil.experimentos.experiments.runner import ExperimentRunner

CONFIGS_CONHECIDAS = (
    "base+temp+priors",
    "base+temp+priors+lua",
    "base+temp+priors+clima",
    "base+temp+priors+lua+clima",
)


@dataclass(frozen=True)
class ResultadoBacktestLab:
    report: dict
    warnings: list[str] = field(default_factory=list)


def rodar_backtest_lab(
    configs: list[str],
    start_concurso: int,
    end_concurso: int,
    retrain_every: int = BACKTEST_RETRAIN_EVERY,
) -> ResultadoBacktestLab:
    """Roda walk-forward (treina em N, prevê N+1) para as configs dadas.

    Levanta ValueError para qualquer entrada inválida — nenhum treino é
    iniciado nesses casos.
    """
    if not configs:
        raise ValueError("Selecione ao menos uma config para o backtest.")

    invalidas = [c for c in configs if c not in CONFIGS_CONHECIDAS]
    if invalidas:
        raise ValueError(f"Configs inválidas: {', '.join(invalidas)}")

    if start_concurso >= end_concurso:
        raise ValueError(
            f"start_concurso ({start_concurso}) deve ser menor que end_concurso ({end_concurso})."
        )

    draws = load_draws()
    if not draws:
        raise ValueError("Nenhum dado histórico encontrado.")

    concursos = [d.concurso for d in draws]
    if end_concurso > concursos[-1]:
        raise ValueError(
            f"end_concurso ({end_concurso}) além do último concurso disponível ({concursos[-1]})."
        )

    start_idx = next((i for i, c in enumerate(concursos) if c >= start_concurso), len(concursos))
    if start_idx >= len(concursos):
        raise ValueError(f"start_concurso ({start_concurso}) além do intervalo de dados disponível.")

    warnings: list[str] = []
    effective_start = start_concurso
    if start_idx < BACKTEST_MIN_TRAIN:
        if BACKTEST_MIN_TRAIN >= len(concursos):
            raise ValueError(
                "Histórico insuficiente para qualquer backtest (mínimo: "
                f"{BACKTEST_MIN_TRAIN} concursos de treino)."
            )
        effective_start = concursos[BACKTEST_MIN_TRAIN]
        if effective_start > end_concurso:
            raise ValueError(
                f"Intervalo [{start_concurso}, {end_concurso}] não deixa "
                f"{BACKTEST_MIN_TRAIN} concursos de histórico antes do início."
            )
        warnings.append(
            f"Início ajustado de {start_concurso} para {effective_start} "
            f"(mínimo de {BACKTEST_MIN_TRAIN} concursos de treino)."
        )

    n_test = sum(1 for c in concursos if effective_start <= c <= end_concurso)
    feature_configs = [FeatureConfig.from_signature(sig) for sig in configs]

    runner = ExperimentRunner(draws)
    report = runner.run(
        n_test=n_test,
        retrain_every=retrain_every,
        configs=feature_configs,
        run_neural=True,
        period_end=end_concurso,
    )
    return ResultadoBacktestLab(report=report, warnings=warnings)
```

**Correction found during implementation (Task 1, commit `ee11388`):** `ExperimentRunner._filter_period(period_start, period_end)` filters the *entire* draws pool passed to `walk_forward`, not just the evaluation window — so passing `period_start=effective_start` here starves `walk_forward` of the pre-`effective_start` history it needs to reach `BACKTEST_MIN_TRAIN`, and no neural config ever gets trained. Only `period_end` is passed to `runner.run()`; `effective_start` is still used (as above) purely to size `n_test` and to build the "insufficient history" warning. This was caught by the no-leakage test itself (TDD did its job) — see the Task 1 report for the full trace.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd lotofacil && pytest testes/unidade/servicos/test_rodar_backtest_lab.py -v`
Expected: PASS (6 tests). The no-leakage test will take a few seconds (real `FrequencyBaseline`/`RandomBaseline` still run for real — only `NeuralModular` is faked).

- [ ] **Step 5: Commit**

```bash
git add lotofacil/src/lotofacil/servicos/rodar_backtest_lab.py lotofacil/testes/unidade/servicos/test_rodar_backtest_lab.py
git commit -m "$(cat <<'EOF'
feat(lab): add rodar_backtest_lab service for walk-forward backtests

Thin, validated wrapper over the existing ExperimentRunner/walk_forward
engine — no changes to the underlying no-leakage walk-forward logic.
EOF
)"
```

---

## Task 2: `TreinoRegistry` — `backtests` table

**Files:**
- Modify: `lotofacil/src/lotofacil/interface/painel/treino_registry.py`
- Test: `lotofacil/src/lotofacil/interface/painel/tests/test_treino_registry.py`

**Interfaces:**
- Consumes: nothing from Task 1.
- Produces: `TreinoRegistry.criar_backtest(backtest_id: str, configs: list[str], start_concurso: int, end_concurso: int, retrain_every: int) -> dict`, `.registrar_resultado_backtest(backtest_id: str, resultado_path: str) -> None`, `.marcar_falha_backtest(backtest_id: str) -> None`, `.listar_backtests() -> list[dict]`, `.buscar_backtest(backtest_id: str) -> dict | None`, `.deletar_backtest(backtest_id: str) -> bool`. Row dicts have keys: `id, configs (decoded list), start_concurso, end_concurso, retrain_every, status, resultado_path, criado_em, concluido_em`.

- [ ] **Step 1: Write the failing tests**

Append to `lotofacil/src/lotofacil/interface/painel/tests/test_treino_registry.py`:

```python
def test_criar_e_buscar_backtest(reg):
    reg.criar_backtest("bt_001", ["base+temp+priors"], 100, 200, 25)
    bt = reg.buscar_backtest("bt_001")
    assert bt["status"] == "running"
    assert bt["configs"] == ["base+temp+priors"]
    assert bt["start_concurso"] == 100
    assert bt["end_concurso"] == 200
    assert bt["retrain_every"] == 25


def test_registrar_resultado_backtest_marca_completed(reg):
    reg.criar_backtest("bt_002", ["base+temp+priors"], 100, 200, 25)
    reg.registrar_resultado_backtest("bt_002", "/tmp/backtest_bt_002.json")
    bt = reg.buscar_backtest("bt_002")
    assert bt["status"] == "completed"
    assert bt["resultado_path"] == "/tmp/backtest_bt_002.json"
    assert bt["concluido_em"] is not None


def test_marcar_falha_backtest(reg):
    reg.criar_backtest("bt_003", ["base+temp+priors"], 100, 200, 25)
    reg.marcar_falha_backtest("bt_003")
    bt = reg.buscar_backtest("bt_003")
    assert bt["status"] == "failed"


def test_listar_backtests_ordenado_por_criacao_desc(reg):
    reg.criar_backtest("bt_004", ["base+temp+priors"], 1, 2, 1)
    reg.criar_backtest("bt_005", ["base+temp+priors+lua"], 1, 2, 1)
    listagem = reg.listar_backtests()
    assert [b["id"] for b in listagem] == ["bt_005", "bt_004"]


def test_deletar_backtest(reg):
    reg.criar_backtest("bt_006", ["base+temp+priors"], 1, 2, 1)
    assert reg.deletar_backtest("bt_006") is True
    assert reg.buscar_backtest("bt_006") is None


def test_buscar_backtest_inexistente_retorna_none(reg):
    assert reg.buscar_backtest("nao_existe") is None
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd lotofacil && pytest src/lotofacil/interface/painel/tests/test_treino_registry.py -v`
Expected: FAIL — `AttributeError: 'TreinoRegistry' object has no attribute 'criar_backtest'`

- [ ] **Step 3: Add the `backtests` table to `_SCHEMA`**

In `treino_registry.py`, modify `_SCHEMA` (around line 11-46) to add a new table right after the `jogos_gerados` table definition and before the closing `"""`:

```python
_SCHEMA = """
CREATE TABLE IF NOT EXISTS treinos (
    id TEXT PRIMARY KEY,
    nome TEXT NOT NULL,
    tipo_config TEXT NOT NULL,
    parametros TEXT NOT NULL,
    arquivo_modelo TEXT,
    metricas TEXT,
    status TEXT NOT NULL DEFAULT 'running',
    criado_em TEXT NOT NULL,
    concluido_em TEXT
);

CREATE TABLE IF NOT EXISTS job_output (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id  TEXT NOT NULL,
    text     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS job_status (
    task_id     TEXT PRIMARY KEY,
    done        INTEGER NOT NULL DEFAULT 0,
    success     INTEGER,
    created_at  TEXT,
    finished_at TEXT
);

CREATE TABLE IF NOT EXISTS jogos_gerados (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    treino_id  TEXT NOT NULL,
    treino_nome TEXT NOT NULL,
    concurso   INTEGER NOT NULL,
    jogos      TEXT NOT NULL,
    criado_em  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS backtests (
    id TEXT PRIMARY KEY,
    configs TEXT NOT NULL,
    start_concurso INTEGER NOT NULL,
    end_concurso INTEGER NOT NULL,
    retrain_every INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'running',
    resultado_path TEXT,
    criado_em TEXT NOT NULL,
    concluido_em TEXT
);
"""
```

- [ ] **Step 4: Add `_row_to_dict_backtest` helper**

In `treino_registry.py`, right after the existing `_row_to_dict` function (around line 57-65), add:

```python
def _row_to_dict_backtest(row: sqlite3.Row) -> dict:
    d = dict(row)
    if d.get("configs"):
        try:
            d["configs"] = json.loads(d["configs"])
        except Exception:
            pass
    return d
```

- [ ] **Step 5: Recover orphaned backtests on startup**

In `treino_registry.py`, in `_recover_orphans()` (around line 84-107), add a `backtests` UPDATE right after the existing `treinos` UPDATE, so a server restart mid-backtest doesn't leave a row stuck as `running` forever:

```python
    def _recover_orphans(self) -> None:
        """Mark treinos/backtests stuck as 'running' from a previous server instance as failed."""
        now = _now()
        with self._conn() as conn:
            conn.execute(
                "UPDATE treinos SET status = 'failed', concluido_em = ? "
                "WHERE status = 'running'",
                (now,),
            )
            conn.execute(
                "UPDATE backtests SET status = 'failed', concluido_em = ? "
                "WHERE status = 'running'",
                (now,),
            )
            # Find all incomplete jobs so we can write a recovery message to each
            orphan_jobs = conn.execute(
                "SELECT task_id FROM job_status WHERE done = 0"
            ).fetchall()
            for row in orphan_jobs:
                conn.execute(
                    "INSERT INTO job_output (task_id, text) VALUES (?, ?)",
                    (row[0], "⚠️  Treino interrompido: servidor reiniciado durante o treinamento."),
                )
            conn.execute(
                "UPDATE job_status SET done = 1, success = 0, finished_at = ? "
                "WHERE done = 0",
                (now,),
            )
            conn.commit()
```

- [ ] **Step 6: Add the CRUD methods**

In `treino_registry.py`, right after `listar_jogos` (end of the "Jogos gerados" section, before the `# ── Job output ──` comment), add:

```python
    # ── Backtests ────────────────────────────────────────────────

    def criar_backtest(
        self, backtest_id: str, configs: list[str],
        start_concurso: int, end_concurso: int, retrain_every: int,
    ) -> dict:
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO backtests "
                "(id, configs, start_concurso, end_concurso, retrain_every, status, criado_em) "
                "VALUES (?, ?, ?, ?, ?, 'running', ?)",
                (backtest_id, json.dumps(configs, ensure_ascii=False),
                 start_concurso, end_concurso, retrain_every, _now()),
            )
        return self.buscar_backtest(backtest_id)

    def registrar_resultado_backtest(self, backtest_id: str, resultado_path: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE backtests SET resultado_path = ?, status = 'completed', concluido_em = ? WHERE id = ?",
                (str(resultado_path), _now(), backtest_id),
            )

    def marcar_falha_backtest(self, backtest_id: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE backtests SET status = 'failed', concluido_em = ? WHERE id = ?",
                (_now(), backtest_id),
            )

    def listar_backtests(self) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM backtests ORDER BY criado_em DESC"
            ).fetchall()
        return [_row_to_dict_backtest(r) for r in rows]

    def buscar_backtest(self, backtest_id: str) -> dict | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM backtests WHERE id = ?", (backtest_id,)
            ).fetchone()
        return _row_to_dict_backtest(row) if row else None

    def deletar_backtest(self, backtest_id: str) -> bool:
        with self._conn() as conn:
            cur = conn.execute("DELETE FROM backtests WHERE id = ?", (backtest_id,))
        return cur.rowcount > 0
```

- [ ] **Step 7: Run the tests to verify they pass**

Run: `cd lotofacil && pytest src/lotofacil/interface/painel/tests/test_treino_registry.py -v`
Expected: PASS (all tests, including the 6 new ones)

- [ ] **Step 8: Commit**

```bash
git add lotofacil/src/lotofacil/interface/painel/treino_registry.py lotofacil/src/lotofacil/interface/painel/tests/test_treino_registry.py
git commit -m "$(cat <<'EOF'
feat(painel): add backtests table to TreinoRegistry

Mirrors the existing treinos CRUD so backtest jobs get the same
persistence, listing and orphan-recovery guarantees as training jobs.
EOF
)"
```

---

## Task 3: CLI command `lotofacil lab backtest`

**Files:**
- Modify: `lotofacil/src/lotofacil/experimentos/main.py`
- Test: `lotofacil/src/lotofacil/experimentos/tests/test_main_backtest_cli.py`

**Interfaces:**
- Consumes: `rodar_backtest_lab`, `ResultadoBacktestLab` from Task 1 (`lotofacil.servicos.rodar_backtest_lab`).
- Produces: CLI command `backtest` (invoked as `lotofacil lab backtest --configs <csv> --start <int> --end <int> --retrain-every <int>`). On success, writes `saida/backtests/backtest_<uuid8>.json` with `{"report": ..., "warnings": [...]}` and prints a line starting with `BACKTEST_RESULT_PATH: ` followed by the absolute path. On `ValueError` from the service, prints the error and exits with code 1 (no file written).

- [ ] **Step 1: Write the failing test**

```python
"""Smoke tests for the `lab backtest` CLI command."""
from unittest.mock import patch

from typer.testing import CliRunner

from lotofacil.experimentos.main import app
from lotofacil.servicos.rodar_backtest_lab import ResultadoBacktestLab

runner = CliRunner()


def test_backtest_command_writes_result_path(tmp_path):
    fake_resultado = ResultadoBacktestLab(
        report={"results": [
            {"name": "neural_base+temp+priors", "mean_hits": 9.5, "n_evaluated": 10},
        ]},
        warnings=[],
    )
    with patch(
        "lotofacil.servicos.rodar_backtest_lab.rodar_backtest_lab",
        return_value=fake_resultado,
    ), patch("lotofacil.experimentos.config.PROJECT_ROOT", tmp_path):
        result = runner.invoke(
            app,
            ["backtest", "--configs", "base+temp+priors", "--start", "100", "--end", "110"],
        )

    assert result.exit_code == 0, result.stdout
    assert "BACKTEST_RESULT_PATH:" in result.stdout
    written = list((tmp_path / "saida" / "backtests").glob("backtest_*.json"))
    assert len(written) == 1


def test_backtest_command_reports_value_error(tmp_path):
    with patch(
        "lotofacil.servicos.rodar_backtest_lab.rodar_backtest_lab",
        side_effect=ValueError("intervalo inválido"),
    ):
        result = runner.invoke(
            app,
            ["backtest", "--configs", "base+temp+priors", "--start", "200", "--end", "100"],
        )

    assert result.exit_code == 1
    assert "intervalo inválido" in result.stdout
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd lotofacil && pytest src/lotofacil/experimentos/tests/test_main_backtest_cli.py -v`
Expected: FAIL — `assert 2 == 0` (Typer reports "No such command 'backtest'")

- [ ] **Step 3: Add the command**

In `lotofacil/src/lotofacil/experimentos/main.py`, insert a new command right after the `ablation` command (after its function body ends, before the `# ── compare ──` comment):

```python
# ── backtest ───────────────────────────────────────────────────────────────────

@app.command("backtest")
def backtest(
    configs_str: str = typer.Option(
        ..., "--configs",
        help="Comma-separated config signatures, e.g. 'base+temp+priors,base+temp+priors+lua'",
    ),
    start: int = typer.Option(..., "--start", help="First concurso to test (inclusive)."),
    end: int = typer.Option(..., "--end", help="Last concurso to test (inclusive)."),
    retrain_every: int = typer.Option(50, "--retrain-every", help="Retrain every N test steps."),
    debug: bool = typer.Option(False, "--debug"),
) -> None:
    """Leak-free walk-forward backtest for one or more lab neural configs over a concurso range."""
    _setup_logging(debug)
    import json
    import uuid
    from lotofacil.experimentos.config import PROJECT_ROOT
    from lotofacil.servicos.rodar_backtest_lab import rodar_backtest_lab

    configs = [c.strip() for c in configs_str.split(",") if c.strip()]
    console.print(
        f"Backtest: configs={configs} start={start} end={end} retrain_every={retrain_every}"
    )

    try:
        resultado = rodar_backtest_lab(configs, start, end, retrain_every)
    except ValueError as exc:
        console.print(f"[red]Erro:[/red] {exc}")
        raise typer.Exit(1)

    for w in resultado.warnings:
        console.print(f"[yellow]Aviso:[/yellow] {w}")

    for entry in resultado.report["results"]:
        if "error" in entry:
            console.print(f"[red]{entry.get('name')}: ERRO — {entry['error']}[/red]")
            continue
        console.print(
            f"{entry['name']}: mean_hits={entry.get('mean_hits', 0):.4f} "
            f"n={entry.get('n_evaluated', 0)}"
        )

    out_dir = PROJECT_ROOT / "saida" / "backtests"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"backtest_{uuid.uuid4().hex[:8]}.json"
    out_path.write_text(
        json.dumps(
            {"report": resultado.report, "warnings": resultado.warnings},
            ensure_ascii=False, indent=2, default=str,
        ),
        encoding="utf-8",
    )
    print(f"BACKTEST_RESULT_PATH: {out_path}", flush=True)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd lotofacil && pytest src/lotofacil/experimentos/tests/test_main_backtest_cli.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add lotofacil/src/lotofacil/experimentos/main.py lotofacil/src/lotofacil/experimentos/tests/test_main_backtest_cli.py
git commit -m "$(cat <<'EOF'
feat(lab): add `lotofacil lab backtest` CLI command

Runs rodar_backtest_lab and writes a JSON result file, printing a
BACKTEST_RESULT_PATH marker line the dashboard subprocess runner
captures to register the result.
EOF
)"
```

---

## Task 4: Flask routes `/api/backtests/*`

**Files:**
- Modify: `lotofacil/src/lotofacil/interface/painel/server.py`
- Test: `lotofacil/src/lotofacil/interface/painel/tests/test_server_backtest.py`

**Interfaces:**
- Consumes: `CONFIGS_CONHECIDAS` from Task 1, `TreinoRegistry.{criar_backtest,registrar_resultado_backtest,marcar_falha_backtest,listar_backtests,buscar_backtest,deletar_backtest}` from Task 2, the existing generic `_run_command(task_id, registry, cmd, cwd, on_complete=None)` and `_concurso_num(p: Path) -> int` helpers already in `server.py`.
- Produces: `POST /api/backtests/iniciar`, `GET /api/backtests`, `GET /api/backtests/<id>`, `DELETE /api/backtests/<id>`. Progress/cancel reuse the existing `/api/jobs/<task_id>/poll` and `/api/jobs/<task_id>/cancel` routes unchanged.

- [ ] **Step 1: Write the failing tests**

```python
"""Tests for the /api/backtests/* endpoints (walk-forward backtest jobs)."""
import json

import pytest

from lotofacil.interface.painel import server as server_module
from lotofacil.interface.painel.treino_registry import TreinoRegistry
from lotofacil.infra.config import DADOS_DIR

SAMPLE_DIR = DADOS_DIR / "sample"


@pytest.fixture(autouse=True)
def patch_dados_dir(monkeypatch):
    monkeypatch.setattr(server_module, "DADOS_DIR", SAMPLE_DIR)


@pytest.fixture
def client():
    server_module.app.testing = True
    with server_module.app.test_client() as c:
        yield c


@pytest.fixture
def reg(tmp_path, monkeypatch):
    r = TreinoRegistry(tmp_path / "test_treinos.db")
    monkeypatch.setattr(server_module, "_registry", r)
    return r


def test_iniciar_rejeita_configs_vazias(client, reg):
    r = client.post("/api/backtests/iniciar", json={"configs": [], "start": 3641, "end": 3645})
    assert r.status_code == 400


def test_iniciar_rejeita_config_desconhecida(client, reg):
    r = client.post(
        "/api/backtests/iniciar",
        json={"configs": ["nao_existe"], "start": 3641, "end": 3645},
    )
    assert r.status_code == 400


def test_iniciar_rejeita_start_maior_que_end(client, reg):
    r = client.post(
        "/api/backtests/iniciar",
        json={"configs": ["base+temp+priors"], "start": 3645, "end": 3641},
    )
    assert r.status_code == 400


def test_iniciar_rejeita_end_alem_do_disponivel(client, reg):
    r = client.post(
        "/api/backtests/iniciar",
        json={"configs": ["base+temp+priors"], "start": 3641, "end": 99999},
    )
    assert r.status_code == 400


def test_iniciar_retorna_ids(client, reg, monkeypatch):
    import threading
    monkeypatch.setattr(threading, "Thread", lambda *a, **kw: type("T", (), {"start": lambda s: None})())
    r = client.post(
        "/api/backtests/iniciar",
        json={"configs": ["base+temp+priors"], "start": 3641, "end": 3645, "retrain_every": 25},
    )
    assert r.status_code == 200
    data = r.get_json()
    assert "backtest_id" in data
    assert "task_id" in data
    bt = reg.buscar_backtest(data["backtest_id"])
    assert bt["status"] == "running"
    assert bt["configs"] == ["base+temp+priors"]


def test_listar_backtests(client, reg):
    reg.criar_backtest("bt_1", ["base+temp+priors"], 3641, 3645, 25)
    r = client.get("/api/backtests")
    assert r.status_code == 200
    data = r.get_json()
    assert any(b["id"] == "bt_1" for b in data)


def test_detalhe_backtest_nao_encontrado(client, reg):
    r = client.get("/api/backtests/nao_existe")
    assert r.status_code == 404


def test_detalhe_backtest_inclui_resultado(client, reg, tmp_path):
    reg.criar_backtest("bt_2", ["base+temp+priors"], 3641, 3645, 25)
    resultado_path = tmp_path / "backtest_bt_2.json"
    resultado_path.write_text(json.dumps({"report": {"results": []}, "warnings": []}))
    reg.registrar_resultado_backtest("bt_2", str(resultado_path))

    r = client.get("/api/backtests/bt_2")
    assert r.status_code == 200
    data = r.get_json()
    assert data["status"] == "completed"
    assert data["resultado"]["report"]["results"] == []


def test_deletar_backtest(client, reg):
    reg.criar_backtest("bt_3", ["base+temp+priors"], 3641, 3645, 25)
    r = client.delete("/api/backtests/bt_3")
    assert r.status_code == 200
    assert reg.buscar_backtest("bt_3") is None


def test_deletar_backtest_nao_encontrado(client, reg):
    r = client.delete("/api/backtests/nao_existe")
    assert r.status_code == 404
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd lotofacil && pytest src/lotofacil/interface/painel/tests/test_server_backtest.py -v`
Expected: FAIL — 404s / `AssertionError` since the routes don't exist yet.

- [ ] **Step 3: Import `CONFIGS_CONHECIDAS`**

In `server.py`, near the other `lotofacil.servicos.*` imports (right after the `from lotofacil.servicos.roi_lab import (...)` block, around line 26-29), add:

```python
from lotofacil.servicos.rodar_backtest_lab import CONFIGS_CONHECIDAS
```

- [ ] **Step 4: Add the result-path extraction helper**

In `server.py`, right after `_extract_model_path_from_output` (around line 1126-1140), add:

```python
def _extract_backtest_result_path_from_output(lines: list[str]) -> str | None:
    for i, line in enumerate(lines):
        if line.startswith("BACKTEST_RESULT_PATH:"):
            rest = line.split(":", 1)[1].strip()
            if not rest and i + 1 < len(lines):
                rest = lines[i + 1].strip()
                j = i + 2
                while not rest.endswith(".json") and j < len(lines):
                    rest += lines[j].strip()
                    j += 1
            return rest or None
    return None
```

- [ ] **Step 5: Add the routes**

In `server.py`, insert this new section right before the `@app.route("/api/jogos-gerados")` route:

```python
# ─── Backtest — API routes ──────────────────────────────────────

@app.route("/api/backtests/iniciar", methods=["POST"])
def api_backtests_iniciar():
    body = request.get_json(force=True) or {}
    configs = body.get("configs") or []
    start = body.get("start")
    end = body.get("end")
    retrain_every = int(body.get("retrain_every") or 50)

    if not configs or not isinstance(configs, list):
        return jsonify({"error": "Selecione ao menos uma config."}), 400
    invalidas = [c for c in configs if c not in CONFIGS_CONHECIDAS]
    if invalidas:
        return jsonify({"error": f"Configs inválidas: {', '.join(invalidas)}"}), 400
    if not isinstance(start, int) or not isinstance(end, int):
        return jsonify({"error": "start/end devem ser inteiros."}), 400
    if start >= end:
        return jsonify({"error": f"start ({start}) deve ser menor que end ({end})."}), 400

    files = sorted(DADOS_DIR.glob("concurso_*.json"), key=_concurso_num)
    if files:
        max_concurso = _concurso_num(files[-1])
        if end > max_concurso:
            return jsonify({
                "error": f"end ({end}) além do último concurso disponível ({max_concurso})."
            }), 400

    backtest_id = uuid.uuid4().hex[:8]
    _registry.criar_backtest(backtest_id, configs, start, end, retrain_every)

    cmd = [
        "lotofacil", "lab", "backtest",
        "--configs", ",".join(configs),
        "--start", str(start),
        "--end", str(end),
        "--retrain-every", str(retrain_every),
    ]
    task_id = f"backtest_{int(time.time() * 1000)}_{backtest_id}"
    _registry.create_job(task_id)

    def on_done(success: bool, output_lines: list[str]):
        if success:
            result_path = _extract_backtest_result_path_from_output(output_lines)
            if result_path and Path(result_path).exists():
                _registry.registrar_resultado_backtest(backtest_id, result_path)
                LOGGER.info("BACKTEST %s registered: %s", backtest_id, result_path)
            else:
                _registry.marcar_falha_backtest(backtest_id)
                LOGGER.warning("BACKTEST %s succeeded but result path missing", backtest_id)
        else:
            _registry.marcar_falha_backtest(backtest_id)
            LOGGER.warning("BACKTEST %s failed", backtest_id)

    t = threading.Thread(
        target=_run_command,
        args=(task_id, _registry, cmd, str(BASE_DIR)),
        kwargs={"on_complete": on_done},
        daemon=True,
    )
    t.start()
    return jsonify({"backtest_id": backtest_id, "task_id": task_id})


@app.route("/api/backtests")
def api_backtests_listar():
    return jsonify(_registry.listar_backtests())


@app.route("/api/backtests/<backtest_id>")
def api_backtest_detalhe(backtest_id: str):
    bt = _registry.buscar_backtest(backtest_id)
    if not bt:
        return jsonify({"error": "Não encontrado"}), 404
    resultado_path = bt.get("resultado_path")
    if resultado_path and Path(resultado_path).exists():
        try:
            bt["resultado"] = json.loads(Path(resultado_path).read_text(encoding="utf-8"))
        except Exception as exc:
            LOGGER.warning("BACKTEST %s: falha ao ler resultado: %s", backtest_id, exc)
    return jsonify(bt)


@app.route("/api/backtests/<backtest_id>", methods=["DELETE"])
def api_backtest_deletar(backtest_id: str):
    if not _registry.deletar_backtest(backtest_id):
        return jsonify({"error": "Não encontrado"}), 404
    return jsonify({"ok": True})
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `cd lotofacil && pytest src/lotofacil/interface/painel/tests/test_server_backtest.py -v`
Expected: PASS (9 tests)

- [ ] **Step 7: Run the full painel test suite to check for regressions**

Run: `cd lotofacil && pytest src/lotofacil/interface/painel/tests/ -v`
Expected: PASS (all tests, old and new)

- [ ] **Step 8: Commit**

```bash
git add lotofacil/src/lotofacil/interface/painel/server.py lotofacil/src/lotofacil/interface/painel/tests/test_server_backtest.py
git commit -m "$(cat <<'EOF'
feat(painel): add /api/backtests/* endpoints

Starts backtests as background subprocess jobs via the existing
_run_command runner, reusing /api/jobs/*/poll and /cancel unchanged.
EOF
)"
```

---

## Task 5: Sidebar tab + page skeleton

**Files:**
- Modify: `lotofacil/src/lotofacil/interface/painel/static/dashboard.html`

**Interfaces:**
- Produces: sidebar tab `backtest`, container `#tab-backtest`, `renderBacktestPage()` (creates `#backtestForm`, `#backtestResults`, `#backtestHistory` containers and calls `_renderBacktestForm()` + `_loadBacktestHistory()` — both stubbed here, replaced by real implementations in Tasks 6 and 9).

- [ ] **Step 1: Add the tab container div**

In `dashboard.html`, in the `content-split` block (around line 887-895), add a new div alongside the other `tab-*` containers:

```html
      <!-- Modelos Tab — populado por renderModelosPage() -->
      <div id="tab-modelos" style="display:none;flex:1;overflow:hidden;flex-direction:column"></div>
      <!-- ROI Lab Tab — populado por renderRoiLab() -->
      <div id="tab-roi-lab" style="display:none;flex:1;overflow:auto;flex-direction:column"></div>
      <!-- Geração Tab — populado por renderGeracao() -->
      <div id="tab-geracao" style="display:none;flex:1;overflow:auto;flex-direction:column"></div>
      <!-- Backtest Tab — populado por renderBacktestPage() -->
      <div id="tab-backtest" style="display:none;flex:1;overflow:auto;flex-direction:column"></div>
      <!-- Jogos Tab — populado por renderJogosPage() -->
      <div id="tab-jogos" style="display:none;flex:1;overflow:auto;flex-direction:column"></div>
```

- [ ] **Step 2: Add the sidebar entry**

In `dashboard.html`, modify `CATEGORIES` (around line 1307-1311):

```js
const CATEGORIES = [
  { id: 'coleta',   icon: '📥', label: 'Coleta'   },
  { id: 'modelos',  icon: '🧠', label: 'Modelos'  },
  { id: 'backtest', icon: '📉', label: 'Backtest' },
  { id: 'jogos',    icon: '🎲', label: 'Jogos'    },
];
```

- [ ] **Step 3: Wire `switchTab`**

In `dashboard.html`, in `switchTab()` (around line 1403-1454):

Change the tab-display block to include the new tab:

```js
  tabModelos.style.display = id === 'modelos' ? 'flex' : 'none';
  document.getElementById('tab-roi-lab').style.display = id === 'roi_lab' ? 'flex' : 'none';
  document.getElementById('tab-geracao').style.display = id === 'geracao' ? 'flex' : 'none';
  document.getElementById('tab-backtest').style.display = id === 'backtest' ? 'flex' : 'none';
  document.getElementById('tab-jogos').style.display = id === 'jogos' ? 'flex' : 'none';
  const consoleTrigger = document.getElementById('consoleTrigger');
  if (consoleTrigger) consoleTrigger.style.display = (id === 'modelos' || id === 'roi_lab' || id === 'geracao' || id === 'backtest' || id === 'jogos') ? 'none' : '';
```

Add a new branch right before the final `} else {` in the same function:

```js
  } else if (id === 'backtest') {
    numSec.style.display = 'none';
    bar.innerHTML = '<div class="section-title">📉 Backtest de Modelos</div>';
    renderBacktestPage();
  } else if (id === 'jogos') {
```

(i.e. the existing `else if (id === 'jogos') { ... }` branch stays exactly as-is; only the new `backtest` branch is inserted immediately before it.)

- [ ] **Step 4: Add the page skeleton + stubs**

In `dashboard.html`, add this new function near `renderJogosPage()` (same area as the other `render*Page` functions):

```js
function renderBacktestPage() {
  const container = document.getElementById('tab-backtest');
  container.innerHTML = `
    <div class="backtest-page" style="padding:1rem;display:flex;flex-direction:column;gap:1rem">
      <div id="backtestForm"></div>
      <div id="backtestResults"></div>
      <div id="backtestHistory"></div>
    </div>`;
  _renderBacktestForm();
  _loadBacktestHistory();
}

function _renderBacktestForm() {
  const el = document.getElementById('backtestForm');
  if (!el) return;
  el.innerHTML = `<div style="color:var(--muted);font-size:0.75rem">Carregando formulário…</div>`;
}

function _loadBacktestHistory() {
  const el = document.getElementById('backtestHistory');
  if (!el) return;
  el.innerHTML = `<div style="color:var(--muted);font-size:0.75rem">Carregando histórico…</div>`;
}
```

- [ ] **Step 5: Manual verification**

Run: `cd lotofacil && source venv/bin/activate && python -m lotofacil.interface.painel.server` (or whatever the project's existing dev-server command is — check `lotofacil/CLAUDE.md` / `commands.py` if unsure) and open the dashboard in a browser.

Expected: sidebar shows Coleta / Modelos / Backtest / Jogos, in that order. Clicking "Backtest" shows the section title "📉 Backtest de Modelos" and two "Carregando…" placeholders, with no errors in the browser console.

- [ ] **Step 6: Commit**

```bash
git add lotofacil/src/lotofacil/interface/painel/static/dashboard.html
git commit -m "$(cat <<'EOF'
feat(dashboard): add Backtest tab skeleton

New top-level sidebar tab wired into switchTab(); form/results/history
containers are stubbed here and filled in by follow-up commits.
EOF
)"
```

---

## Task 6: Backtest form

**Files:**
- Modify: `lotofacil/src/lotofacil/interface/painel/static/dashboard.html`

**Interfaces:**
- Consumes: `#backtestForm` container from Task 5, `GET /api/status` (existing route), `POST /api/backtests/iniciar` from Task 4.
- Produces: replaces the `_renderBacktestForm` stub with the real form; calls `openBacktestModal(taskId, backtestId, totalSteps)` on submit (implemented in Task 7 — declared here as a forward reference, safe because JS function declarations are hoisted and this call only fires on a later user click, by which point Task 7's code will exist in the same file).

- [ ] **Step 1: Replace `_renderBacktestForm` and add the submit handler**

In `dashboard.html`, replace the Task-5 stub for `_renderBacktestForm` with:

```js
const BACKTEST_CONFIGS = [
  { sig: 'base+temp+priors',           label: 'Padrão' },
  { sig: 'base+temp+priors+lua',       label: '+ Lua' },
  { sig: 'base+temp+priors+clima',     label: '+ Clima' },
  { sig: 'base+temp+priors+lua+clima', label: '+ Lua + Clima' },
];

async function _renderBacktestForm() {
  const el = document.getElementById('backtestForm');
  if (!el) return;

  let maxConcurso = 0, minConcurso = 1;
  try {
    const status = await fetch('/api/status').then(r => r.json());
    maxConcurso = (status.last_concurso && status.last_concurso.concurso) || 0;
    const totalDraws = status.total_draws || 0;
    minConcurso = totalDraws ? Math.max(1, maxConcurso - totalDraws + 1) : 1;
  } catch (e) {
    logClient('warn', 'Falha ao carregar status para backtest', { error: e.message });
  }

  const defaultEnd = maxConcurso || 100;
  const defaultStart = Math.max(minConcurso, defaultEnd - 50);

  const checks = BACKTEST_CONFIGS.map((c, i) => `
    <label style="display:flex;align-items:center;gap:0.35rem;font-size:0.78rem;cursor:pointer">
      <input type="checkbox" class="backtest-config-check" value="${c.sig}" ${i === 0 ? 'checked' : ''}>
      ${esc(c.label)}
    </label>`).join('');

  el.innerHTML = `
    <div style="border:1px solid var(--border);border-radius:8px;padding:1rem">
      <div class="section-title" style="margin-bottom:0.6rem">🧪 Novo Backtest</div>
      <div style="display:flex;flex-direction:column;gap:0.25rem;margin-bottom:0.75rem">
        ${checks}
      </div>
      <div style="display:flex;gap:0.75rem;flex-wrap:wrap;align-items:flex-end;margin-bottom:0.5rem">
        <div>
          <label style="display:block;font-size:0.68rem;color:var(--muted)">Concurso inicial</label>
          <input type="number" id="backtestStart" value="${defaultStart}" min="${minConcurso}" max="${maxConcurso}"
            style="width:90px;padding:3px 6px;background:var(--surface);color:var(--text);border:1px solid var(--border);border-radius:3px">
        </div>
        <div>
          <label style="display:block;font-size:0.68rem;color:var(--muted)">Concurso final</label>
          <input type="number" id="backtestEnd" value="${defaultEnd}" min="${minConcurso}" max="${maxConcurso}"
            style="width:90px;padding:3px 6px;background:var(--surface);color:var(--text);border:1px solid var(--border);border-radius:3px">
        </div>
        <div>
          <label style="display:block;font-size:0.68rem;color:var(--muted)">Retrain a cada</label>
          <input type="number" id="backtestRetrainEvery" value="50" min="1" max="500"
            style="width:70px;padding:3px 6px;background:var(--surface);color:var(--text);border:1px solid var(--border);border-radius:3px">
        </div>
        <button class="action-btn" id="backtestSubmitBtn" onclick="_iniciarBacktest()">▶ Iniciar Backtest</button>
      </div>
      <div id="backtestEstimate" style="font-size:0.68rem;color:var(--dim)"></div>
      <div id="backtestFormError" style="font-size:0.72rem;color:#e57373;margin-top:0.4rem"></div>
    </div>`;

  const updateEstimate = () => {
    const start = parseInt(document.getElementById('backtestStart').value) || 0;
    const end = parseInt(document.getElementById('backtestEnd').value) || 0;
    const retrainEvery = parseInt(document.getElementById('backtestRetrainEvery').value) || 1;
    const nConfigs = document.querySelectorAll('.backtest-config-check:checked').length;
    const span = Math.max(0, end - start + 1);
    const retreinos = retrainEvery > 0 ? Math.ceil(span / retrainEvery) : span;
    document.getElementById('backtestEstimate').textContent = span > 0
      ? `~${span} concursos testados · ~${retreinos} retreino(s) por modelo · ${nConfigs} modelo(s) selecionado(s)`
      : '';
  };
  el.querySelectorAll('#backtestStart, #backtestEnd, #backtestRetrainEvery').forEach(i => i.addEventListener('input', updateEstimate));
  el.querySelectorAll('.backtest-config-check').forEach(i => i.addEventListener('change', updateEstimate));
  updateEstimate();
}

async function _iniciarBacktest() {
  const configs = [...document.querySelectorAll('.backtest-config-check:checked')].map(i => i.value);
  const start = parseInt(document.getElementById('backtestStart').value);
  const end = parseInt(document.getElementById('backtestEnd').value);
  const retrainEvery = parseInt(document.getElementById('backtestRetrainEvery').value) || 50;
  const errEl = document.getElementById('backtestFormError');
  errEl.textContent = '';

  if (!configs.length) { errEl.textContent = 'Selecione ao menos uma config.'; return; }
  if (!Number.isFinite(start) || !Number.isFinite(end) || start >= end) {
    errEl.textContent = 'Concurso inicial deve ser menor que o final.';
    return;
  }

  const btn = document.getElementById('backtestSubmitBtn');
  btn.disabled = true;
  btn.textContent = 'Iniciando…';
  try {
    const res = await fetch('/api/backtests/iniciar', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ configs, start, end, retrain_every: retrainEvery }),
    });
    const data = await res.json();
    if (!res.ok) {
      errEl.textContent = data.error || 'Falha ao iniciar backtest.';
      return;
    }
    openBacktestModal(data.task_id, data.backtest_id, configs.length + 2);
  } catch (e) {
    errEl.textContent = 'Erro de rede ao iniciar backtest.';
    logClient('error', 'Falha ao iniciar backtest', { error: e.message });
  } finally {
    btn.disabled = false;
    btn.textContent = '▶ Iniciar Backtest';
  }
}
```

- [ ] **Step 2: Manual verification**

Start the dashboard, open the Backtest tab. Expected: form renders with 4 config checkboxes (Padrão pre-checked), start/end/retrain-every inputs pre-filled from `/api/status`, and an estimate line that updates live as you change any field. Clicking "Iniciar Backtest" with no config checked shows the inline error "Selecione ao menos uma config." without a network call. Checking a config and clicking the button again triggers `POST /api/backtests/iniciar` (visible in the browser Network tab) — it's fine that it currently throws `openBacktestModal is not defined` in the console, since that function doesn't exist until Task 7.

- [ ] **Step 3: Commit**

```bash
git add lotofacil/src/lotofacil/interface/painel/static/dashboard.html
git commit -m "$(cat <<'EOF'
feat(dashboard): add Backtest form (configs, concurso range, retrain)

Client-side validation before submit; estimate line shows expected
retrains per model as the user adjusts the range/retrain_every.
EOF
)"
```

---

## Task 7: Backtest progress modal

**Files:**
- Modify: `lotofacil/src/lotofacil/interface/painel/static/dashboard.html`

**Interfaces:**
- Consumes: `GET /api/jobs/<task_id>/poll`, `POST /api/jobs/<task_id>/cancel` (existing, unmodified routes), `_backtestModalResultId` flows into `_loadBacktestResult(backtestId)` (Task 8) and `_loadBacktestHistory()` (Task 5 stub, replaced in Task 9) on successful close — both safe forward references (called only from a user-driven `closeBacktestModal()` click, after the whole file has loaded).
- Produces: `openBacktestModal(taskId: string, backtestId: string, totalSteps: number)`, `cancelBacktest()`, `closeBacktestModal()`.

- [ ] **Step 1: Add the modal markup**

In `dashboard.html`, right after the closing `</div>` of the existing `<!-- Modal de progresso de treino -->` block (`treinoModalOverlay`), add:

```html
<!-- Modal de progresso de backtest -->
<div class="treino-modal-overlay" id="backtestModalOverlay">
  <div class="treino-modal">
    <div class="treino-modal-header">
      <h3 id="backtestModalTitle">Rodando backtest…</h3>
      <span class="treino-modal-status" id="backtestModalStatus"></span>
    </div>
    <div class="treino-progress-bar">
      <div class="treino-progress-fill" id="backtestProgressFill"></div>
    </div>
    <div class="treino-epoch-label" id="backtestStepLabel">Iniciando…</div>
    <div class="treino-log" id="backtestLog"></div>
    <div class="treino-modal-footer">
      <button class="treino-cancel-btn" id="backtestCancelBtn" onclick="cancelBacktest()">✕ Cancelar</button>
      <button class="treino-close-btn" id="backtestCloseBtn" onclick="closeBacktestModal()" disabled>✓ Fechar</button>
    </div>
  </div>
</div>
```

- [ ] **Step 2: Add the modal JS**

In `dashboard.html`, right after `closeTreinoModal()` (end of the treino modal JS block), add:

```js
let _backtestPoller = null;
let _backtestTaskId = null;
let _backtestPollOffset = 0;
let _backtestTotalSteps = 1;
let _backtestStepsDone = 0;
let _backtestModalResultId = null;

function openBacktestModal(taskId, backtestId, totalSteps) {
  _backtestTaskId = taskId;
  _backtestPollOffset = 0;
  _backtestTotalSteps = totalSteps || 1;
  _backtestStepsDone = 0;

  document.getElementById('backtestModalTitle').textContent = 'Rodando backtest…';
  document.getElementById('backtestModalStatus').textContent = 'Em andamento · 00:00';
  document.getElementById('backtestProgressFill').style.width = '0%';
  document.getElementById('backtestProgressFill').style.background = '';
  document.getElementById('backtestStepLabel').textContent = 'Iniciando…';
  document.getElementById('backtestLog').innerHTML = '';
  document.getElementById('backtestCancelBtn').disabled = false;
  document.getElementById('backtestCloseBtn').disabled = true;
  document.getElementById('backtestModalOverlay').classList.add('visible');

  const modalStart = Date.now();
  window._backtestElapsedTimer = setInterval(() => {
    if (!_backtestPoller) { clearInterval(window._backtestElapsedTimer); return; }
    const sec = Math.floor((Date.now() - modalStart) / 1000);
    const mm = String(Math.floor(sec / 60)).padStart(2, '0');
    const ss = String(sec % 60).padStart(2, '0');
    document.getElementById('backtestModalStatus').textContent = `Em andamento · ${mm}:${ss}`;
  }, 1000);

  _backtestPoller = setInterval(() => _pollBacktest(backtestId), 2000);
}

async function _pollBacktest(backtestId) {
  if (!_backtestTaskId) return;
  try {
    const res = await fetch(`/api/jobs/${_backtestTaskId}/poll?offset=${_backtestPollOffset}`);
    const data = await res.json();

    if (data.lines && data.lines.length > 0) {
      _backtestPollOffset = data.next_offset;
      _appendBacktestLog(data.lines);
      _updateBacktestProgressFromLog(data.lines);
    }

    if (data.done) {
      clearInterval(_backtestPoller);
      _backtestPoller = null;
      _finishBacktestModal(data.success !== false, backtestId);
    }
  } catch (e) {
    logClient('warn', 'Falha no poll do backtest', { error: e.message });
  }
}

function _appendBacktestLog(lines) {
  const log = document.getElementById('backtestLog');
  for (const line of lines) {
    if (!line) continue;
    const div = document.createElement('div');
    if (/^✅|sucesso|conclu/i.test(line)) div.className = 'log-success';
    else if (/^❌|erro|error|Traceback/i.test(line)) div.className = 'log-error';
    else if (/^\$/.test(line)) div.className = 'log-cmd';
    div.textContent = line;
    log.appendChild(div);
  }
  while (log.children.length > 60) log.removeChild(log.firstChild);
  log.scrollTop = log.scrollHeight;
}

function _updateBacktestProgressFromLog(lines) {
  for (const line of lines) {
    if (/Running (random baseline|frequency baseline|neural config)/.test(line)) {
      _backtestStepsDone += 1;
    }
  }
  const pct = Math.min(100, Math.round((_backtestStepsDone / _backtestTotalSteps) * 100));
  document.getElementById('backtestProgressFill').style.width = `${pct}%`;
  document.getElementById('backtestStepLabel').textContent =
    `${Math.min(_backtestStepsDone, _backtestTotalSteps)}/${_backtestTotalSteps} etapas · ${pct}%`;
}

function _finishBacktestModal(success, backtestId) {
  clearInterval(window._backtestElapsedTimer);
  const title = document.getElementById('backtestModalTitle');
  const status = document.getElementById('backtestModalStatus');
  const fill = document.getElementById('backtestProgressFill');
  document.getElementById('backtestCancelBtn').disabled = true;
  document.getElementById('backtestCloseBtn').disabled = false;

  if (success) {
    title.textContent = '✅ Backtest concluído';
    fill.style.width = '100%';
    fill.style.background = 'var(--green)';
    status.textContent = 'Resultado pronto. Clique Fechar para ver.';
    showToast('✅ Backtest concluído!', 'success');
  } else {
    title.textContent = '❌ Backtest falhou';
    status.textContent = 'Veja o log para detalhes.';
    showToast('❌ Backtest falhou. Verifique o log no modal.', 'error');
  }
  _backtestModalResultId = backtestId;
}

async function cancelBacktest() {
  if (!_backtestTaskId) return;
  document.getElementById('backtestCancelBtn').disabled = true;
  try {
    await fetch(`/api/jobs/${_backtestTaskId}/cancel`, { method: 'POST' });
  } catch (e) { /* silencioso — pode já ter terminado */ }
  clearInterval(_backtestPoller);
  _backtestPoller = null;
  closeBacktestModal();
}

function closeBacktestModal() {
  clearInterval(window._backtestElapsedTimer);
  const wasSuccess = document.getElementById('backtestModalTitle').textContent.includes('✅');
  document.getElementById('backtestModalOverlay').classList.remove('visible');
  _backtestTaskId = null;
  _backtestPollOffset = 0;
  if (wasSuccess && _backtestModalResultId) {
    _loadBacktestResult(_backtestModalResultId);
    _loadBacktestHistory();
  }
  _backtestModalResultId = null;
}
```

- [ ] **Step 3: Manual verification**

Start the dashboard, open Backtest, pick a small concurso range (e.g. 5 concursos) with `retrain_every` large enough that it only retrains once or twice, and submit. Expected: the progress modal opens immediately, the elapsed timer ticks every second, the log tail fills in as the subprocess prints (baseline lines first, then `Running neural config: ...`), and the progress bar/step label advance. Confirm "Cancelar" (clicked mid-run) stops the job and closes the modal, and that on natural completion the title turns "✅ Backtest concluído" and "Fechar" becomes enabled. It's fine that clicking "Fechar" now throws `_loadBacktestResult is not defined` in the console — that lands in Task 8.

- [ ] **Step 4: Commit**

```bash
git add lotofacil/src/lotofacil/interface/painel/static/dashboard.html
git commit -m "$(cat <<'EOF'
feat(dashboard): add backtest progress modal

Polls the existing /api/jobs/*/poll route; step progress is derived
from the "Running <baseline|neural config>" log lines ExperimentRunner
already emits, since neural retrain counts vary too much for a
per-epoch bar across a whole backtest range.
EOF
)"
```

---

## Task 8: Backtest results (table + chart + histogram)

**Files:**
- Modify: `lotofacil/src/lotofacil/interface/painel/static/dashboard.html`

**Interfaces:**
- Consumes: `GET /api/backtests/<id>` from Task 4 (response shape: `{..., status, resultado: {report: {results: [...]}, warnings: [...]}}`, or no `resultado` key if not yet completed).
- Produces: `_loadBacktestResult(backtestId: string)` (fetches and renders — called from Task 7's `closeBacktestModal()` and from Task 9's history click).

- [ ] **Step 1: Add the result-loading and rendering functions**

In `dashboard.html`, add near the other `render*` helpers (e.g. right after the Task 7 modal JS block):

```js
async function _loadBacktestResult(backtestId) {
  const el = document.getElementById('backtestResults');
  if (!el) return;
  el.innerHTML = `<div style="color:var(--muted);font-size:0.75rem">Carregando resultado…</div>`;
  try {
    const data = await fetch(`/api/backtests/${backtestId}`).then(r => r.json());
    _renderBacktestResult(data);
  } catch (e) {
    el.innerHTML = `<div style="color:#e57373;font-size:0.75rem">Falha ao carregar resultado.</div>`;
    logClient('error', 'Falha ao carregar resultado do backtest', { error: e.message });
  }
}

function _renderBacktestResult(data) {
  const el = document.getElementById('backtestResults');
  if (!el) return;

  if (data.status !== 'completed' || !data.resultado) {
    el.innerHTML = `<div style="color:var(--muted);font-size:0.75rem">
      Backtest ${esc(data.status || '?')} — sem resultado disponível.
    </div>`;
    return;
  }

  const warnings = data.resultado.warnings || [];
  const results = (data.resultado.report && data.resultado.report.results) || [];
  const ok = results.filter(r => !r.error);
  const sorted = [...ok].sort((a, b) => (b.mean_hits || 0) - (a.mean_hits || 0));

  const warnHtml = warnings.length
    ? `<div style="font-size:0.7rem;color:#f0ad4e;margin-bottom:0.5rem">${warnings.map(esc).join('<br>')}</div>`
    : '';

  const rows = sorted.map(r => `
    <tr>
      <td style="padding:3px 8px;font-size:0.75rem">${esc(r.name)}</td>
      <td style="padding:3px 8px;font-size:0.75rem;text-align:right">${r.n_evaluated ?? '—'}</td>
      <td style="padding:3px 8px;font-size:0.75rem;text-align:right">${(r.mean_hits ?? 0).toFixed(3)}</td>
      <td style="padding:3px 8px;font-size:0.75rem;text-align:right">${((r.rate_ge_11 || 0) * 100).toFixed(1)}%</td>
      <td style="padding:3px 8px;font-size:0.75rem;text-align:right">${((r.rate_ge_13 || 0) * 100).toFixed(1)}%</td>
      <td style="padding:3px 8px;font-size:0.75rem;text-align:right">${(r.roi_pct ?? 0).toFixed(1)}%</td>
      <td style="padding:3px 8px;font-size:0.75rem;text-align:right">${r.p_value_vs_random ?? '—'}</td>
    </tr>`).join('');

  el.innerHTML = `
    <div style="border:1px solid var(--border);border-radius:8px;padding:1rem">
      <div class="section-title" style="margin-bottom:0.5rem">📊 Resultado do Backtest</div>
      ${warnHtml}
      <div style="overflow-x:auto">
        <table style="width:100%;border-collapse:collapse">
          <tr>
            <th style="font-size:0.7rem;text-align:left;padding:3px 8px">Modelo</th>
            <th style="font-size:0.7rem;text-align:right;padding:3px 8px">Testados</th>
            <th style="font-size:0.7rem;text-align:right;padding:3px 8px">Média acertos</th>
            <th style="font-size:0.7rem;text-align:right;padding:3px 8px">≥11</th>
            <th style="font-size:0.7rem;text-align:right;padding:3px 8px">≥13</th>
            <th style="font-size:0.7rem;text-align:right;padding:3px 8px">ROI%</th>
            <th style="font-size:0.7rem;text-align:right;padding:3px 8px">p-valor</th>
          </tr>
          ${rows}
        </table>
      </div>
      <canvas id="backtestHitsCanvas" width="900" height="200"
        style="width:100%;margin-top:0.75rem;border:1px solid var(--border);border-radius:4px;background:var(--surface)"></canvas>
      <div id="backtestHitsDist" style="margin-top:0.6rem"></div>
    </div>`;

  requestAnimationFrame(() => {
    _drawBacktestHitsChart(sorted);
    _renderBacktestHitsDist(sorted);
  });
}

const _BACKTEST_SERIES_COLORS = ['#4fc3f7', '#ce93d8', '#81c784', '#ffb74d', '#e57373', '#90a4ae'];

function _drawBacktestHitsChart(entries) {
  const canvas = document.getElementById('backtestHitsCanvas');
  if (!canvas || !entries.length) return;
  const ctx = canvas.getContext('2d');
  const W = canvas.width, H = canvas.height, PAD = 28;

  const series = entries.map(e => (e.raw_results || []).map(r => r.hits)).filter(pts => pts.length > 0);
  if (!series.length) return;

  const allVals = series.flat();
  const minV = Math.min(0, ...allVals);
  const maxV = Math.max(15, ...allVals);
  const range = maxV - minV || 1;
  const maxLen = Math.max(...series.map(s => s.length));
  const toX = i => PAD + (i / (maxLen - 1 || 1)) * (W - PAD * 2);
  const toY = v => H - PAD - ((v - minV) / range) * (H - PAD * 2);

  ctx.clearRect(0, 0, W, H);
  entries.forEach((entry, idx) => {
    const pts = (entry.raw_results || []).map(r => r.hits);
    if (!pts.length) return;
    const isNeural = entry.name && entry.name.startsWith('neural_');
    ctx.save();
    ctx.strokeStyle = _BACKTEST_SERIES_COLORS[idx % _BACKTEST_SERIES_COLORS.length];
    ctx.lineWidth = isNeural ? 2 : 1.5;
    if (!isNeural) ctx.setLineDash([5, 3]);
    ctx.beginPath();
    pts.forEach((v, i) => i === 0 ? ctx.moveTo(toX(i), toY(v)) : ctx.lineTo(toX(i), toY(v)));
    ctx.stroke();
    ctx.restore();
  });

  ctx.font = '10px monospace';
  entries.forEach((entry, idx) => {
    ctx.fillStyle = _BACKTEST_SERIES_COLORS[idx % _BACKTEST_SERIES_COLORS.length];
    ctx.fillText(entry.name, PAD + idx * 140, 14);
  });
}

function _renderBacktestHitsDist(entries) {
  const el = document.getElementById('backtestHitsDist');
  if (!el) return;
  const keys = ['11', '12', '13', '14', '15'];
  const header = `<th style="font-size:0.7rem;text-align:left;padding:2px 6px">Acertos</th>` +
    entries.map(e => `<th style="font-size:0.7rem;text-align:right;padding:2px 6px">${esc(e.name)}</th>`).join('');
  const rows = keys.map(k => {
    const cells = entries.map(e => `<td style="padding:2px 6px;font-size:0.72rem;text-align:right">${(e.hits_distribution || {})[k] || 0}</td>`).join('');
    return `<tr><td style="padding:2px 6px;font-size:0.72rem">${k} acertos</td>${cells}</tr>`;
  }).join('');
  el.innerHTML = `<div style="overflow-x:auto"><table style="border-collapse:collapse"><tr>${header}</tr>${rows}</table></div>`;
}
```

- [ ] **Step 2: Manual verification**

Run a small backtest to completion (per Task 7's verification) and click "Fechar" on the success modal. Expected: the results panel shows a comparison table sorted by mean hits descending (including `random` and `frequency` baseline rows), a line chart with one series per model (dashed for baselines, solid for the neural config), and a 5-row (11–15) histogram table with one column per model. Reload the page and manually call `_loadBacktestResult('<the backtest id from history>')` from the browser console to confirm it re-renders identically from persisted data.

- [ ] **Step 3: Commit**

```bash
git add lotofacil/src/lotofacil/interface/painel/static/dashboard.html
git commit -m "$(cat <<'EOF'
feat(dashboard): render backtest comparison table, hits chart, histogram

Canvas-drawn per-concurso hits chart and 11-15 histogram, following
the same hand-rolled canvas approach already used for the ROI Lab
equity curve — no new charting dependency.
EOF
)"
```

---

## Task 9: Backtest history

**Files:**
- Modify: `lotofacil/src/lotofacil/interface/painel/static/dashboard.html`

**Interfaces:**
- Consumes: `GET /api/backtests`, `DELETE /api/backtests/<id>` from Task 4; `_loadBacktestResult` from Task 8.
- Produces: replaces the `_loadBacktestHistory` stub from Task 5 with the real implementation; adds `_renderBacktestHistory(items)` and `_deletarBacktest(id)`.

- [ ] **Step 1: Replace the history stub**

In `dashboard.html`, replace the Task-5 stub for `_loadBacktestHistory` with:

```js
async function _loadBacktestHistory() {
  const el = document.getElementById('backtestHistory');
  if (!el) return;
  el.innerHTML = `<div style="color:var(--muted);font-size:0.75rem">Carregando histórico…</div>`;
  try {
    const items = await fetch('/api/backtests').then(r => r.json());
    _renderBacktestHistory(items);
  } catch (e) {
    el.innerHTML = `<div style="color:#e57373;font-size:0.75rem">Falha ao carregar histórico.</div>`;
    logClient('error', 'Falha ao carregar histórico de backtests', { error: e.message });
  }
}

function _renderBacktestHistory(items) {
  const el = document.getElementById('backtestHistory');
  if (!el) return;
  if (!items.length) {
    el.innerHTML = `<div class="empty-state" style="padding:1rem 0">
      <span class="big-icon">📉</span>
      <p>Nenhum backtest executado ainda.</p>
    </div>`;
    return;
  }
  const statusLabel = { running: '⏳ Em andamento', completed: '✅ Concluído', failed: '❌ Falhou' };
  const rows = items.map(b => `
    <tr style="cursor:pointer" onclick="_loadBacktestResult('${esc(b.id)}')">
      <td style="padding:4px 8px;font-size:0.75rem">${esc((b.criado_em || '').slice(0, 16).replace('T', ' '))}</td>
      <td style="padding:4px 8px;font-size:0.75rem">${(b.configs || []).map(esc).join(', ')}</td>
      <td style="padding:4px 8px;font-size:0.75rem;text-align:right">${b.start_concurso}–${b.end_concurso}</td>
      <td style="padding:4px 8px;font-size:0.75rem;text-align:right">${b.retrain_every}</td>
      <td style="padding:4px 8px;font-size:0.75rem">${statusLabel[b.status] || esc(b.status)}</td>
      <td style="padding:4px 8px">
        <button class="action-btn" style="padding:1px 5px;font-size:0.65rem"
          onclick="event.stopPropagation();_deletarBacktest('${esc(b.id)}')">🗑</button>
      </td>
    </tr>`).join('');

  el.innerHTML = `
    <div style="border:1px solid var(--border);border-radius:8px;padding:1rem">
      <div class="section-title" style="margin-bottom:0.5rem">🕑 Histórico de Backtests</div>
      <div style="overflow-x:auto">
        <table style="width:100%;border-collapse:collapse">
          <tr>
            <th style="font-size:0.7rem;text-align:left;padding:4px 8px">Data</th>
            <th style="font-size:0.7rem;text-align:left;padding:4px 8px">Configs</th>
            <th style="font-size:0.7rem;text-align:right;padding:4px 8px">Intervalo</th>
            <th style="font-size:0.7rem;text-align:right;padding:4px 8px">Retrain</th>
            <th style="font-size:0.7rem;text-align:left;padding:4px 8px">Status</th>
            <th></th>
          </tr>
          ${rows}
        </table>
      </div>
    </div>`;
}

async function _deletarBacktest(id) {
  try {
    await fetch(`/api/backtests/${id}`, { method: 'DELETE' });
    _loadBacktestHistory();
  } catch (e) {
    logClient('error', 'Falha ao deletar backtest', { error: e.message });
  }
}
```

- [ ] **Step 2: Manual verification**

Open the Backtest tab. Expected: the history table lists all past runs (most recent first), each row showing date, configs, concurso range, retrain_every, and status. Clicking a row loads that run's results into the results panel above (reusing Task 8's renderer) without re-running anything. Clicking the 🗑 button on a row removes it from the list without navigating into its results (confirm `event.stopPropagation()` prevents the row-click handler from also firing). With zero runs (fresh `treinos.db`), confirm the empty-state message shows instead of an empty table.

- [ ] **Step 3: Commit**

```bash
git add lotofacil/src/lotofacil/interface/painel/static/dashboard.html
git commit -m "$(cat <<'EOF'
feat(dashboard): add backtest history list

Completes the Backtest tab: past runs are listed, revisitable, and
deletable without re-running the underlying walk-forward simulation.
EOF
)"
```
