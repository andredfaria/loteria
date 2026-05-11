# Unified CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace 3 fragmented CLIs + root scripts with a single `lotofacil` entry point organized in domain groups, archive legacy code, and add `.gitignore`.

**Architecture:** New `src/cli/` package with `app.py` as root Typer app. Sub-apps `dados`, `modelo`, `portfolio`, `lab` registered via `add_typer`. Top-level `prever` command defined in `app.py`. All business logic imported from existing modules — no ML code rewritten. `pyproject.toml` entry point updated to `src.cli.app:app`.

**Tech Stack:** Python 3.11+, Typer, Rich, existing `lotofacil_ml`, `strategies`, `lotofacil_lab` modules.

---

## File Map

| Action | Path |
|---|---|
| Create | `src/cli/__init__.py` |
| Create | `src/cli/app.py` |
| Create | `src/cli/dados.py` |
| Create | `src/cli/modelo.py` |
| Create | `src/cli/portfolio.py` |
| Create | `src/cli/lab.py` |
| Create | `.gitignore` |
| Create | `legacy/` (archive — git mv from multiple paths) |
| Modify | `pyproject.toml` (entry point only) |
| Modify | `tests/test_portfolio.py` (update import path) |
| Modify | `README.md` (Quick Start section) |

---

## Task 1: Archive legacy code to `legacy/`

**Files:**
- `src/analise/` → `legacy/analise/`
- `src/coleta/` → `legacy/coleta/`
- `src/estrategia/` → `legacy/estrategia/`
- `src/geracao/` → `legacy/geracao/`
- `src/sugestao/` → `legacy/sugestao/`
- `src/validacao/` → `legacy/validacao/`
- `src/dashboard/` → `legacy/dashboard/`
- `portfolio/` → `legacy/portfolio/`
- Root scripts → `legacy/scripts/`

- [ ] **Step 1: Create legacy/ and move src legacy modules**

```bash
mkdir -p legacy/scripts
git mv src/analise legacy/analise
git mv src/coleta legacy/coleta
git mv src/estrategia legacy/estrategia
git mv src/geracao legacy/geracao
git mv src/sugestao legacy/sugestao
git mv src/validacao legacy/validacao
git mv src/dashboard legacy/dashboard
```

- [ ] **Step 2: Move root-level scripts and portfolio/**

```bash
git mv predict_portfolio.py legacy/scripts/predict_portfolio.py
git mv portfolio legacy/portfolio
```

Check for any other root scripts to move:
```bash
ls *.py
```
Move any found (`predict_3680.py`, `backtest_peso_ml.py`, `train_ensemble.py`, `predict_15_from_11.py`):
```bash
for f in predict_3680.py backtest_peso_ml.py train_ensemble.py predict_15_from_11.py; do
    [ -f "$f" ] && git mv "$f" legacy/scripts/"$f"
done
```

- [ ] **Step 3: Add legacy/README.md**

```bash
cat > legacy/README.md << 'EOF'
# legacy/

Código arquivado — superado por módulos em `src/`.

| Pasta | Substituído por |
|---|---|
| `analise/` | `lotofacil modelo backtest` |
| `coleta/` | `lotofacil dados atualizar` |
| `estrategia/` | `src/strategies/` |
| `geracao/` | `src/strategies/eleven_numbers/` |
| `sugestao/` | `src/lotofacil_ml/models/` |
| `validacao/` | `lotofacil modelo validar` |
| `dashboard/` | `src/cli/` |
| `portfolio/` | `src/cli/portfolio.py` |
| `scripts/` | `src/cli/` commands |
EOF
```

- [ ] **Step 4: Verify existing tests still pass**

```bash
cd /home/andre/Documentos/projetos/loteria/lotofacil && source venv/bin/activate
pytest tests/ -v 2>&1 | tail -20
```

Expected: same pass/fail as before (test_portfolio.py will fail — fixed in Task 7).

- [ ] **Step 5: Commit**

```bash
git add legacy/ src/
git commit -m "refactor: archive legacy code to legacy/"
```

---

## Task 2: Add `.gitignore`

**Files:**
- Create: `.gitignore`

- [ ] **Step 1: Create .gitignore**

```bash
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.pyc
*.pyo
*.pyd
*.egg-info/
dist/
build/
.eggs/

# Virtual environments
venv/
.venv/
env/

# Database & models (generated artifacts)
src/lotofacil.db
src/models_saved/
src/lotofacil_lab/saved_models/
output/models/

# Generated output
saida/
output/reports/
output/predictions/

# Data (except committed sample)
dados/clima/
dados/processed/
dados/*.csv
dados/all_draws.json
ml/datasets/
ml/modelos/
ml/models/

# IDE
.cursor/
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db

# Portfolio outputs (generated)
portfolio_*.txt
EOF
```

- [ ] **Step 2: Commit**

```bash
git add .gitignore
git commit -m "chore: add .gitignore"
```

---

## Task 3: Bootstrap `src/cli/` package

**Files:**
- Create: `src/cli/__init__.py`
- Create: `src/cli/app.py`

- [ ] **Step 1: Write failing import test**

```python
# tests/test_cli_smoke.py
def test_cli_app_importable():
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
    from cli.app import app
    assert app is not None
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
pytest tests/test_cli_smoke.py -v
```

Expected: `ModuleNotFoundError: No module named 'cli'`

- [ ] **Step 3: Create `src/cli/__init__.py`**

```python
```
(empty file)

- [ ] **Step 4: Create `src/cli/app.py`**

```python
"""Unified CLI entry point for Lotofácil Prediction System."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

_SRC = Path(__file__).resolve().parent.parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import typer
from rich.console import Console
from rich.panel import Panel
from rich import box

app = typer.Typer(
    name="lotofacil",
    help="Sistema de previsão Lotofácil — dados, modelos, portfólio e experimentos.",
    add_completion=False,
)
console = Console()


@app.command()
def prever(
    approach: str = typer.Option(
        "all", "--approach", "-a",
        help="Abordagem: statistical, ml, neural, all",
    ),
    concurso: Optional[int] = typer.Option(None, "--concurso", "-c", help="Concurso alvo"),
) -> None:
    """Prediz 11 números para o próximo concurso."""
    from data.loader import load_draws
    from strategies.eleven_numbers.predictor import ElevenNumbersStrategy

    draws = load_draws(source="db")
    if not draws:
        console.print("[red]Sem dados. Execute: lotofacil dados atualizar --all[/red]")
        raise typer.Exit(1)

    strategy = ElevenNumbersStrategy()
    pred = strategy.predict(draws, approach=approach)

    dezenas_str = "  ".join(f"{n:02d}" for n in sorted(pred.dezenas))
    console.print()
    console.print(Panel(
        f"[bold cyan]Predição — Concurso {pred.concurso_alvo}[/bold cyan]\n\n"
        f"[yellow]{dezenas_str}[/yellow]\n\n"
        f"Abordagem: [dim]{pred.approach}[/dim]\n"
        f"Confiança: [green]{pred.confianca_media:.4f}[/green]",
        box=box.DOUBLE_EDGE,
    ))


def _register_subapps() -> None:
    from cli.dados import app as dados_app
    from cli.modelo import app as modelo_app
    from cli.portfolio import app as portfolio_app
    from cli.lab import app as lab_app

    app.add_typer(dados_app, name="dados")
    app.add_typer(modelo_app, name="modelo")
    app.add_typer(portfolio_app, name="portfolio")
    app.add_typer(lab_app, name="lab", help="Pipeline experimental — clima, lua, ablação.")


_register_subapps()

if __name__ == "__main__":
    app()
```

- [ ] **Step 5: Run test — should pass now**

```bash
pytest tests/test_cli_smoke.py -v
```

Expected: PASSED

- [ ] **Step 6: Commit**

```bash
git add src/cli/ tests/test_cli_smoke.py
git commit -m "feat(cli): bootstrap src/cli/ package with app.py"
```

---

## Task 4: Implement `src/cli/dados.py`

**Files:**
- Create: `src/cli/dados.py`

- [ ] **Step 1: Add help smoke test to test_cli_smoke.py**

```python
# Append to tests/test_cli_smoke.py
from typer.testing import CliRunner

def test_dados_help():
    from cli.app import app
    runner = CliRunner()
    result = runner.invoke(app, ["dados", "--help"])
    assert result.exit_code == 0
    assert "atualizar" in result.output
    assert "status" in result.output
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
pytest tests/test_cli_smoke.py::test_dados_help -v
```

Expected: error about missing `cli.dados`

- [ ] **Step 3: Create `src/cli/dados.py`**

```python
"""dados subcommands — data update and status."""
from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import typer
from rich.console import Console

app = typer.Typer(help="Gerenciamento de dados — coleta e status.")
console = Console()


@app.command()
def atualizar(
    all: bool = typer.Option(False, "--all", help="Carrega todos os draws dos arquivos locais"),
    latest: bool = typer.Option(False, "--latest", help="Busca apenas o sorteio mais recente da API"),
) -> None:
    """Sincroniza novos concursos da API para o banco de dados."""
    from lotofacil_ml.data.database import DatabaseManager
    from lotofacil_ml.data.fetcher import LotofacilFetcher

    db = DatabaseManager()
    fetcher = LotofacilFetcher(db)

    if all:
        console.print("[cyan]Carregando todos os dados locais...[/cyan]")
        draws = fetcher.fetch_all_results()
        console.print(f"[green]✓ {len(draws)} concursos importados[/green]")
    elif latest:
        console.print("[cyan]Buscando sorteio mais recente da API...[/cyan]")
        draw = fetcher.fetch_latest()
        if draw:
            console.print(f"[green]✓ Concurso {draw['concurso']} ({draw['data']})[/green]")
        else:
            console.print("[red]Não foi possível buscar o sorteio mais recente.[/red]")
            raise typer.Exit(1)
    else:
        console.print("[cyan]Sincronizando novos sorteios...[/cyan]")
        n = fetcher.sync_new_draws()
        console.print(f"[green]✓ {n} novos sorteios sincronizados[/green]")


@app.command()
def status() -> None:
    """Mostra o último concurso, total de draws e período coberto."""
    from data.database import DatabaseManager

    db = DatabaseManager()
    count = db.count_concursos()
    latest = db.get_latest_concurso()

    console.print(f"[bold]Status do banco de dados[/bold]")
    console.print(f"Total de concursos: [cyan]{count}[/cyan]")
    if latest:
        console.print(f"Mais recente: Concurso [cyan]{latest['concurso']}[/cyan] ({latest['data']})")
    else:
        console.print("[yellow]Sem dados. Execute: lotofacil dados atualizar --all[/yellow]")
```

- [ ] **Step 4: Run test**

```bash
pytest tests/test_cli_smoke.py::test_dados_help -v
```

Expected: PASSED

- [ ] **Step 5: Commit**

```bash
git add src/cli/dados.py tests/test_cli_smoke.py
git commit -m "feat(cli): add dados atualizar and status commands"
```

---

## Task 5: Implement `src/cli/modelo.py`

**Files:**
- Create: `src/cli/modelo.py`

- [ ] **Step 1: Add smoke tests**

```python
# Append to tests/test_cli_smoke.py

def test_modelo_help():
    from cli.app import app
    runner = CliRunner()
    result = runner.invoke(app, ["modelo", "--help"])
    assert result.exit_code == 0
    assert "treinar" in result.output
    assert "backtest" in result.output
    assert "historico" in result.output
    assert "validar" in result.output
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
pytest tests/test_cli_smoke.py::test_modelo_help -v
```

Expected: error about missing `cli.modelo`

- [ ] **Step 3: Create `src/cli/modelo.py`**

```python
"""modelo subcommands — training, backtest, history, validate."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

_SRC = Path(__file__).resolve().parent.parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import typer
from rich.console import Console
from rich.table import Table
from rich import box

app = typer.Typer(help="Treino, backtest, histórico e validação dos modelos.")
console = Console()


@app.command()
def treinar(debug: bool = typer.Option(False, "--debug")) -> None:
    """Treina todos os modelos (Frequency + ML Ensemble + LSTM)."""
    from lotofacil_ml.data.database import DatabaseManager
    from lotofacil_ml.models.ensemble import EnsemblePredictor

    db = DatabaseManager()
    draws = db.get_all_concursos()

    if len(draws) < 100:
        console.print("[red]Dados insuficientes. Execute: lotofacil dados atualizar --all[/red]")
        raise typer.Exit(1)

    console.print(f"[cyan]Treinando em {len(draws)} concursos...[/cyan]")
    predictor = EnsemblePredictor()
    predictor.train(draws)
    console.print("[green]✓ Treino concluído. Modelos salvos.[/green]")


@app.command()
def backtest(
    dados_dir: Optional[Path] = typer.Option(None, "--dados", help="Diretório de dados"),
    start: Optional[int] = typer.Option(None, "--start", help="Concurso inicial"),
    end: Optional[int] = typer.Option(None, "--end", help="Concurso final"),
    train_window: int = typer.Option(300, "--train-window"),
    retrain_every: int = typer.Option(50, "--retrain-every"),
    out: Path = typer.Option(Path("saida/relatorio.html"), "--out"),
    debug: bool = typer.Option(False, "--debug"),
) -> None:
    """Roda walk-forward backtest e gera relatório HTML em saida/relatorio.html."""
    import logging
    logging.basicConfig(level=logging.DEBUG if debug else logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                        datefmt="%H:%M:%S")

    from lotofacil_ml.config import PROJECT_ROOT
    from lotofacil_ml.data.loader import load_draws
    from lotofacil_ml.backtest.engine import BacktestEngine, BacktestSummary
    from lotofacil_ml.backtest.baseline import random_game
    from lotofacil_ml.models.frequency_model import FrequencyModel
    from lotofacil_ml.models.frequency_ensemble import FrequencyEnsembleModel
    from lotofacil_ml.models.probabilistic import ProbabilisticModel
    from lotofacil_ml.models.ensemble import EnsemblePredictor
    from lotofacil_ml.report.html_generator import HTMLReportGenerator

    dados = dados_dir or PROJECT_ROOT / "dados"
    prize_table = {11: 7.00, 12: 14.00, 13: 35.00, 14: 2000.00, 15: 1_500_000.00}

    draws = load_draws(dados)
    if len(draws) < 200:
        console.print(f"[red]Dados insuficientes: {len(draws)} concursos (mínimo: 200).[/red]")
        raise typer.Exit(1)
    console.print(f"[green]✓ {len(draws)} concursos carregados[/green]")

    concurso_nums = [d.concurso for d in draws]
    start_idx = (concurso_nums.index(start) if start and start in concurso_nums
                 else max(train_window, len(draws) - 500))
    end_idx = (concurso_nums.index(end) + 1 if end and end in concurso_nums else len(draws))

    model_configs = [
        ("frequency", FrequencyModel),
        ("frequency_ensemble", FrequencyEnsembleModel),
        ("probabilistic", ProbabilisticModel),
        ("ensemble", EnsemblePredictor),
    ]
    summaries = {}
    baseline_results = []

    for name, cls in model_configs:
        console.print(f"[cyan]Rodando backtest: {name}...[/cyan]")
        engine = BacktestEngine(cls(), train_window=train_window, retrain_every=retrain_every)
        results = engine.run(draws, start_idx=start_idx, end_idx=end_idx)
        summaries[name] = BacktestSummary(model_name=name, results=results)
        console.print(f"  [green]✓ {summaries[name].mean_hits:.3f} acertos médios[/green]")
        if not baseline_results:
            for r in results:
                idx = concurso_nums.index(r.concurso)
                rg = random_game()
                hits = len(set(rg) & set(draws[idx].dezenas))
                baseline_results.append(type("BR", (), {"hits": hits, "concurso": r.concurso})())

    out.parent.mkdir(parents=True, exist_ok=True)
    HTMLReportGenerator(cost=3.50, prize_table=prize_table).generate(summaries, baseline_results, out)
    console.print(f"[green]✓ Relatório salvo: {out}[/green]")


@app.command()
def historico(limit: int = typer.Option(20, "--limit", "-l")) -> None:
    """Exibe o histórico de predições (últimas N)."""
    from lotofacil_ml.data.database import DatabaseManager

    db = DatabaseManager()
    records = db.get_prediction_history(limit=limit)

    if not records:
        console.print("[yellow]Nenhum histórico encontrado.[/yellow]")
        return

    table = Table(title=f"Histórico de Predições (últimas {limit})", box=box.SIMPLE_HEAVY)
    table.add_column("Concurso", style="cyan", justify="center")
    table.add_column("Dezenas", style="white")
    table.add_column("Confiança", justify="right")
    table.add_column("Acertos", justify="center")
    table.add_column("Data", style="dim")

    for r in records:
        dezenas_str = " ".join(f"{d:02d}" for d in r["dezenas_sugeridas"])
        acertos = str(r["acertos"]) if r["acertos"] is not None else "—"
        table.add_row(
            str(r["concurso_alvo"]),
            dezenas_str,
            f"{r['confianca_media']:.4f}",
            acertos,
            r["criado_em"][:16] if r["criado_em"] else "—",
        )
    console.print(table)


@app.command()
def validar(debug: bool = typer.Option(False, "--debug")) -> None:
    """Valida predições pendentes contra resultados reais."""
    from lotofacil_ml.data.database import DatabaseManager

    db = DatabaseManager()
    pending = db.get_pending_validations()
    all_draws = {d["concurso"]: d for d in db.get_all_concursos()}

    if not pending:
        console.print("[yellow]Nenhuma predição pendente de validação.[/yellow]")
        return

    validated = 0
    for pred in pending:
        concurso = pred["concurso_alvo"]
        if concurso in all_draws:
            actual = all_draws[concurso]["dezenas"]
            hits = len(set(pred["dezenas_sugeridas"]) & set(actual))
            db.update_validation(concurso, hits)
            console.print(f"[green]Concurso {concurso}: {hits} acertos[/green]")
            validated += 1

    if not validated:
        console.print("[yellow]Nenhuma predição pôde ser validada (sorteios ainda não disponíveis).[/yellow]")
    else:
        console.print(f"\n[green]✓ {validated} predição(ões) validada(s)[/green]")
```

- [ ] **Step 4: Run test**

```bash
pytest tests/test_cli_smoke.py::test_modelo_help -v
```

Expected: PASSED

- [ ] **Step 5: Commit**

```bash
git add src/cli/modelo.py tests/test_cli_smoke.py
git commit -m "feat(cli): add modelo treinar/backtest/historico/validar commands"
```

---

## Task 6: Implement `src/cli/portfolio.py`

**Files:**
- Create: `src/cli/portfolio.py`
- Modify: `tests/test_portfolio.py` (update import path)

- [ ] **Step 1: Add smoke test**

```python
# Append to tests/test_cli_smoke.py

def test_portfolio_help():
    from cli.app import app
    runner = CliRunner()
    result = runner.invoke(app, ["portfolio", "--help"])
    assert result.exit_code == 0
    assert "validar" in result.output
```

- [ ] **Step 2: Run failing test**

```bash
pytest tests/test_cli_smoke.py::test_portfolio_help -v
```

Expected: error about missing `cli.portfolio`

- [ ] **Step 3: Create `src/cli/portfolio.py`**

Move all pure functions from `predict_portfolio.py` (now in `legacy/scripts/`) plus wrap them in Typer commands.

```python
"""portfolio command — generate and validate Lotofácil game portfolios."""
from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
import requests

_SRC = Path(__file__).resolve().parent.parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import typer
from rich.console import Console
from rich.table import Table
from rich import box

app = typer.Typer(invoke_without_command=True)
console = Console()

COST_PER_GAME = 3.50
API_BASE = "https://loteriascaixa-api.herokuapp.com/api/lotofacil"
API_TIMEOUT = 15

_PRIMOS = {2, 3, 5, 7, 11, 13, 17, 19, 23}
_FIBONACCI = {1, 2, 3, 5, 8, 13, 21}
_MOLDURA = {1, 2, 3, 4, 5, 21, 22, 23, 24, 25}

_DIST_TABLE = {
    1: (1, 0, 0), 2: (2, 0, 0), 3: (1, 1, 1),
    4: (2, 1, 1), 5: (2, 3, 0), 6: (2, 2, 2),
    7: (3, 2, 2), 8: (3, 3, 2), 9: (3, 3, 3),
    10: (4, 3, 3),
}


def distribute_games(n: int) -> Tuple[int, int, int]:
    """Return (conservador, equilibrado, agressivo) counts summing to n."""
    if n in _DIST_TABLE:
        return _DIST_TABLE[n]
    a = max(1, n // 4)
    c = max(1, round(n * 0.4))
    e = n - c - a
    if e < 0:
        e = 0
        c = n - a
    return (c, e, a)


def game_quality_score(game: List[int], last_draw: List[int]) -> float:
    """Return quality score in [0, 1] based on 7 statistical filters."""
    passed = 0
    pares = sum(1 for n in game if n % 2 == 0)
    if (pares, 15 - pares) in {(7, 8), (8, 7), (6, 9), (9, 6)}:
        passed += 1
    soma = sum(game)
    if 171 <= soma <= 220:
        passed += 1
    if 8 <= sum(1 for n in game if n in _MOLDURA) <= 11:
        passed += 1
    if 4 <= sum(1 for n in game if n in _PRIMOS) <= 7:
        passed += 1
    if 3 <= sum(1 for n in game if n in _FIBONACCI) <= 5:
        passed += 1
    s = sorted(game)
    if any(s[i + 1] == s[i] + 1 for i in range(len(s) - 1)):
        passed += 1
    if 8 <= sum(1 for n in game if n in set(last_draw)) <= 10:
        passed += 1
    return passed / 7


def fetch_missing_draws(dados_dir: Path, target_concurso: int) -> None:
    """Fetch missing concursos up to target_concurso-1 and save JSON files."""
    existing = {
        int(f.stem.split("_")[1])
        for f in dados_dir.glob("concurso_*.json")
        if f.stem.split("_")[1].isdigit()
    }
    max_local = max(existing, default=0)
    needed = list(range(max_local + 1, target_concurso))
    if not needed:
        console.print(f"  Dados já atualizados até concurso {max_local}")
        return
    console.print(f"  Buscando concursos {max_local + 1} → {target_concurso - 1}...")
    session = requests.Session()
    session.headers["User-Agent"] = "lotofacil-portfolio/1.0"
    for n in needed:
        path = dados_dir / f"concurso_{n}.json"
        if path.exists():
            continue
        try:
            resp = session.get(f"{API_BASE}/{n}", timeout=API_TIMEOUT)
            resp.raise_for_status()
            raw = resp.json()
            path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
            console.print(f"    ✓ Concurso {n}: {raw.get('dezenas', [])}")
        except Exception as exc:
            console.print(f"    [red]✗ Concurso {n}: {exc}[/red]")


def load_draws_from_files(dados_dir: Path, max_concurso: int):
    """Load Draw objects from dados_dir where concurso < max_concurso, sorted ascending."""
    from core.models import Draw

    draws = []
    for f in Path(dados_dir).glob("concurso_*.json"):
        parts = f.stem.split("_")
        if len(parts) < 2 or not parts[1].isdigit():
            continue
        try:
            raw = json.loads(f.read_text(encoding="utf-8"))
            n = int(raw["concurso"])
            if n >= max_concurso:
                continue
            dezenas = sorted(int(d) for d in raw["dezenas"])
            if len(dezenas) != 15 or not all(1 <= d <= 25 for d in dezenas):
                continue
            draws.append(Draw(concurso=n, data=raw.get("data", ""), dezenas=dezenas))
        except Exception:
            continue
    draws.sort(key=lambda d: d.concurso)
    return draws


def get_probabilities(draws) -> np.ndarray:
    """Return probability array of shape (25,) — cascade: neural → ensemble → statistical → freq."""
    try:
        from lotofacil_lab.data.feature_flags import FeatureConfig
        from lotofacil_lab.models.neural_modular import NeuralModular
        from lotofacil_lab.features.builder import ModularFeatureBuilder

        cfg = FeatureConfig.from_signature("base+temp+priors+clima+lua")
        model = NeuralModular(cfg)
        model.load()
        builder = ModularFeatureBuilder(draws, cfg)
        x_latest = builder.build_for_prediction()
        probas = np.array(model._model.predict(x_latest, verbose=0)[0], dtype=np.float64)
        if probas.sum() > 0:
            probas /= probas.sum()
        console.print("  [green]Neural (clima+lua) ✓[/green]")
        return probas
    except Exception as e_neural:
        console.print(f"  [yellow]Neural falhou ({e_neural}), tentando ensemble...[/yellow]")

    try:
        from strategies.eleven_numbers.predictor import ElevenNumbersStrategy

        pred = ElevenNumbersStrategy().predict(draws, approach="all")
        probas = np.array(pred.probabilidades, dtype=np.float64)
        if probas.sum() > 0:
            probas /= probas.sum()
        console.print("  [green]Ensemble: estatístico + ML ✓[/green]")
        return probas
    except Exception as e_all:
        console.print(f"  [yellow]Ensemble falhou ({e_all}), tentando estatístico...[/yellow]")

    try:
        from strategies.eleven_numbers.predictor import ElevenNumbersStrategy

        pred = ElevenNumbersStrategy().predict(draws, approach="statistical")
        probas = np.array(pred.probabilidades, dtype=np.float64)
        if probas.sum() > 0:
            probas /= probas.sum()
        console.print("  [green]Estatístico ✓[/green]")
        return probas
    except Exception:
        pass

    counts = np.zeros(25, dtype=np.float64)
    for draw in draws[-100:]:
        for n in draw.dezenas:
            counts[n - 1] += 1
    return counts / counts.sum() if counts.sum() > 0 else np.ones(25) / 25


def generate_games_for_tier(
    core: List[int],
    fill_pool: List[int],
    n_games: int,
    last_draw: List[int],
) -> List[List[int]]:
    """Generate n_games games with all core + 4 from fill_pool, ranked by quality."""
    if n_games == 0:
        return []
    core_set = set(core)
    effective_pool = [n for n in fill_pool if n not in core_set]
    if len(effective_pool) < 4:
        extras = [n for n in range(1, 26) if n not in core_set and n not in effective_pool]
        effective_pool = effective_pool + extras
    effective_pool = effective_pool[:20]

    candidates: List[Tuple[float, List[int]]] = []
    seen: set = set()
    for fill in itertools.combinations(effective_pool, 4):
        game = sorted(list(core) + list(fill))
        key = tuple(game)
        if key in seen:
            continue
        seen.add(key)
        candidates.append((game_quality_score(game, last_draw), game))

    candidates.sort(key=lambda x: (-x[0], x[1]))

    chosen: List[List[int]] = []
    used_fills: List[frozenset] = []
    for score, game in candidates:
        fills = frozenset(n for n in game if n not in core_set)
        if all(len(fills & prev) < 4 for prev in used_fills):
            chosen.append(game)
            used_fills.append(fills)
        if len(chosen) == n_games:
            break

    for score, game in candidates:
        if len(chosen) >= n_games:
            break
        if game not in chosen:
            chosen.append(game)

    return chosen[:n_games]


def build_portfolio(
    core: List[int],
    ranked: List[int],
    n_games: int,
    last_draw: List[int],
) -> dict:
    """Build tiered portfolio (conservador/equilibrado/agressivo)."""
    n_c, n_e, n_a = distribute_games(n_games)
    return {
        "conservador": generate_games_for_tier(core, ranked[11:17], n_c, last_draw),
        "equilibrado": generate_games_for_tier(core, ranked[11:22], n_e, last_draw),
        "agressivo":   generate_games_for_tier(core, ranked[11:25], n_a, last_draw),
    }


def print_portfolio(
    portfolio: dict,
    n_jogos: int,
    target_concurso: int,
    last_draw: Optional[List[int]] = None,
) -> None:
    """Print portfolio with tier headers, quality bars, and cost summary."""
    if last_draw is None:
        last_draw = list(range(1, 16))

    tier_meta = {
        "conservador": ("CONSERVADOR", "Fills: top-6 após o core — menor variação"),
        "equilibrado": ("EQUILIBRADO", "Fills: top-11 após o core — variação moderada"),
        "agressivo":   ("AGRESSIVO",   "Fills: todos após o core — máxima diversidade"),
    }
    total_games = sum(len(v) for v in portfolio.values())
    total_cost = total_games * COST_PER_GAME

    console.print(f"\n[bold]{'═'*58}[/bold]")
    console.print(f"  [bold cyan]PORTFÓLIO LOTOFÁCIL — Concurso {target_concurso}[/bold cyan]")
    console.print(f"  {total_games} jogos · R${total_cost:.2f}")
    console.print(f"[bold]{'═'*58}[/bold]")

    game_idx = 1
    for tier_key in ("conservador", "equilibrado", "agressivo"):
        games = portfolio.get(tier_key, [])
        if not games:
            continue
        label, desc = tier_meta[tier_key]
        plural = "s" if len(games) > 1 else ""
        console.print(f"\n  [bold]── {label} ({len(games)} jogo{plural}) ──[/bold]")
        console.print(f"     [dim]{desc}[/dim]")
        for game in games:
            score = game_quality_score(game, last_draw)
            filters_ok = round(score * 7)
            bar = "█" * filters_ok + "░" * (7 - filters_ok)
            nums = "  ".join(f"{n:02d}" for n in sorted(game))
            soma = sum(game)
            pares = sum(1 for n in game if n % 2 == 0)
            console.print(f"\n  [yellow]Jogo {game_idx:02d}:[/yellow] {nums}")
            console.print(
                f"          Qualidade [[{bar}]] {filters_ok}/7"
                f"  |  Soma {soma}"
                f"  |  {pares}P/{15-pares}I"
                f"  |  R${COST_PER_GAME:.2f}"
            )
            game_idx += 1

    expected_roi = total_games * (
        (1 / 10) * 7.00 + (1 / 55) * 14.00 +
        (1 / 691) * 35.00 + (1 / 21791) * 2_000.00
    )
    console.print(f"\n[dim]{'─'*58}[/dim]")
    console.print(f"  Total: {total_games} jogos · Custo: R${total_cost:.2f}")
    console.print(
        f"  Retorno esperado: R${expected_roi:.2f}"
        f"  (ROI: {(expected_roi - total_cost) / total_cost * 100:.1f}%)"
    )
    console.print(f"[bold]{'═'*58}[/bold]\n")


# ── Typer commands ─────────────────────────────────────────────────────────────

_DADOS_DIR = Path(__file__).resolve().parent.parent.parent / "dados"


@app.callback(invoke_without_command=True)
def portfolio_main(
    ctx: typer.Context,
    concurso: Optional[int] = typer.Option(None, "--concurso", "-c", help="Concurso alvo"),
    jogos: int = typer.Option(2, "--jogos", "-j", help="Número de jogos (padrão: 2)"),
) -> None:
    """Gera portfólio tiered (conservador / equilibrado / agressivo)."""
    if ctx.invoked_subcommand is not None:
        return

    if concurso is None:
        # Infer next concurso from latest local file
        existing = sorted(
            int(f.stem.split("_")[1])
            for f in _DADOS_DIR.glob("concurso_*.json")
            if f.stem.split("_")[1].isdigit()
        )
        concurso = (existing[-1] + 1) if existing else None
        if concurso is None:
            console.print("[red]Não foi possível determinar o concurso alvo. Use --concurso N.[/red]")
            raise typer.Exit(1)

    console.print(f"\n[bold][1/4] Atualizando dados via API...[/bold]")
    fetch_missing_draws(_DADOS_DIR, concurso)

    console.print(f"\n[bold][2/4] Carregando histórico de sorteios...[/bold]")
    draws = load_draws_from_files(_DADOS_DIR, concurso)
    if not draws:
        console.print("[red]Nenhum concurso carregado. Verifique dados/.[/red]")
        raise typer.Exit(1)
    console.print(f"  {len(draws)} concursos ({draws[0].concurso} → {draws[-1].concurso})")
    last_draw = draws[-1].dezenas

    console.print(f"\n[bold][3/4] Calculando probabilidades...[/bold]")
    probas = get_probabilities(draws)
    ranked = [int(x) for x in np.argsort(probas)[::-1] + 1]
    core = ranked[:11]
    console.print(f"  Core 11: {sorted(core)}")

    console.print(f"\n[bold][4/4] Gerando portfólio...[/bold]")
    portfolio = build_portfolio(core, ranked, jogos, last_draw)
    print_portfolio(portfolio, jogos, concurso, last_draw)


@app.command("validar")
def portfolio_validar(
    concurso: int = typer.Argument(..., help="Concurso a validar (ex: 3675)"),
) -> None:
    """Simula e valida portfólio gerado para um concurso já realizado."""
    # Load actual draw result
    result_path = _DADOS_DIR / f"concurso_{concurso}.json"
    if not result_path.exists():
        console.print(f"[red]Sorteio do concurso {concurso} não encontrado em dados/.[/red]")
        console.print("Execute: lotofacil dados atualizar")
        raise typer.Exit(1)

    raw = json.loads(result_path.read_text(encoding="utf-8"))
    actual_dezenas = sorted(int(d) for d in raw["dezenas"])
    console.print(f"\nSorteio real (concurso {concurso}): "
                  + " ".join(f"{n:02d}" for n in actual_dezenas))

    # Regenerate portfolio using data up to concurso-1
    draws = load_draws_from_files(_DADOS_DIR, concurso)
    if not draws:
        console.print("[red]Sem histórico anterior ao concurso informado.[/red]")
        raise typer.Exit(1)

    last_draw = draws[-1].dezenas
    probas = get_probabilities(draws)
    ranked = [int(x) for x in np.argsort(probas)[::-1] + 1]
    core = ranked[:11]
    portfolio = build_portfolio(core, ranked, 8, last_draw)

    table = Table(title=f"Validação — Concurso {concurso}", box=box.SIMPLE_HEAVY)
    table.add_column("Jogo", justify="center", style="cyan")
    table.add_column("Tier")
    table.add_column("Dezenas")
    table.add_column("Acertos", justify="center", style="green")
    table.add_column("Prêmio")

    prize_map = {11: "R$7,00", 12: "R$14,00", 13: "R$35,00", 14: "R$2.000,00", 15: "Jackpot"}
    game_idx = 1
    for tier in ("conservador", "equilibrado", "agressivo"):
        for game in portfolio.get(tier, []):
            hits = len(set(game) & set(actual_dezenas))
            prize = prize_map.get(hits, "—")
            nums = " ".join(f"{n:02d}" for n in sorted(game))
            table.add_row(str(game_idx), tier, nums, str(hits), prize)
            game_idx += 1

    console.print(table)
```

- [ ] **Step 4: Run smoke test**

```bash
pytest tests/test_cli_smoke.py::test_portfolio_help -v
```

Expected: PASSED

- [ ] **Step 5: Update `tests/test_portfolio.py`** to import from `cli.portfolio` instead of loading the old file via importlib

Replace the `_load_portfolio()` helper and all `m = _load_portfolio()` calls:

```python
# tests/test_portfolio.py — top of file (replace imports section)
import json
import sys
import tempfile
from pathlib import Path

_LOTOFACIL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_LOTOFACIL / "src"))

import cli.portfolio as m  # replaces _load_portfolio() dynamic import
```

Then replace every `m = _load_portfolio()` and every `m.function(...)` to just `m.function(...)` (remove `m = _load_portfolio()` lines), since `m` is now the module imported at top level.

Full updated file:

```python
"""Tests for cli/portfolio.py"""
import json
import sys
import tempfile
from pathlib import Path

_LOTOFACIL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_LOTOFACIL / "src"))

import cli.portfolio as m


def test_cost_per_game_is_3_50_core():
    from core.config import COST_PER_GAME
    assert COST_PER_GAME == 3.50


def test_cost_per_game_is_3_50_ml():
    from lotofacil_ml.config import COST_PER_GAME
    assert COST_PER_GAME == 3.50


def test_distribute_games_five():
    c, e, a = m.distribute_games(5)
    assert c + e + a == 5
    assert c >= e >= a >= 1


def test_distribute_games_eight():
    c, e, a = m.distribute_games(8)
    assert c + e + a == 8
    assert c >= e >= a >= 1


def test_distribute_games_one():
    c, e, a = m.distribute_games(1)
    assert c + e + a == 1


def test_game_quality_score_bounds():
    score = m.game_quality_score(
        [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
        [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
    )
    assert 0.0 <= score <= 1.0


def test_game_quality_score_good_game():
    game = [1, 3, 4, 5, 6, 7, 9, 10, 12, 13, 15, 16, 17, 18, 21]
    last = [2, 4, 5, 6, 7, 8, 9, 10, 11, 13, 14, 15, 17, 20, 22]
    score = m.game_quality_score(game, last)
    assert 0.0 <= score <= 1.0


def test_load_draws_from_files_empty_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        result = m.load_draws_from_files(Path(tmpdir), max_concurso=9999)
    assert result == []


def test_load_draws_from_files_respects_max_concurso():
    with tempfile.TemporaryDirectory() as tmpdir:
        d = Path(tmpdir)
        for n, dezenas in [(100, list(range(1, 16))), (200, list(range(2, 17)))]:
            (d / f"concurso_{n}.json").write_text(
                json.dumps({
                    "concurso": n,
                    "data": "01/01/2020",
                    "dezenas": [str(x).zfill(2) for x in dezenas],
                })
            )
        draws = m.load_draws_from_files(d, max_concurso=200)
    assert len(draws) == 1
    assert draws[0].concurso == 100


def test_load_draws_sorted_by_concurso():
    with tempfile.TemporaryDirectory() as tmpdir:
        d = Path(tmpdir)
        for n, dezenas in [(300, list(range(3, 18))), (100, list(range(1, 16)))]:
            (d / f"concurso_{n}.json").write_text(
                json.dumps({
                    "concurso": n,
                    "data": "01/01/2020",
                    "dezenas": [str(x).zfill(2) for x in dezenas],
                })
            )
        draws = m.load_draws_from_files(d, max_concurso=9999)
    assert draws[0].concurso == 100
    assert draws[1].concurso == 300


def test_get_probabilities_shape_and_sum():
    draws = m.load_draws_from_files(
        _LOTOFACIL / "dados" / "sample",
        max_concurso=9999,
    )
    assert len(draws) >= 10
    probas = m.get_probabilities(draws)
    assert probas.shape == (25,)
    assert abs(probas.sum() - 1.0) < 1e-4
    assert all(probas >= 0)


def test_get_probabilities_top11_unique():
    import numpy as np
    draws = m.load_draws_from_files(
        _LOTOFACIL / "dados" / "sample",
        max_concurso=9999,
    )
    probas = m.get_probabilities(draws)
    top11 = list(np.argsort(probas)[::-1][:11] + 1)
    assert len(set(top11)) == 11
    assert all(1 <= n <= 25 for n in top11)


def test_generate_games_for_tier_count():
    core = list(range(1, 12))
    fill_pool = list(range(12, 18))
    last_draw = list(range(1, 16))
    games = m.generate_games_for_tier(core, fill_pool, n_games=3, last_draw=last_draw)
    assert len(games) == 3


def test_generate_games_for_tier_each_game_has_15():
    core = list(range(1, 12))
    fill_pool = list(range(12, 20))
    last_draw = list(range(1, 16))
    games = m.generate_games_for_tier(core, fill_pool, n_games=2, last_draw=last_draw)
    for game in games:
        assert len(game) == 15
        assert len(set(game)) == 15
        assert all(1 <= n <= 25 for n in game)


def test_generate_games_for_tier_contains_core():
    core = [1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21]
    fill_pool = [2, 4, 6, 8, 10, 12, 14, 16]
    last_draw = list(range(1, 16))
    games = m.generate_games_for_tier(core, fill_pool, n_games=2, last_draw=last_draw)
    for game in games:
        assert all(n in game for n in core)


def test_build_portfolio_structure():
    core = list(range(1, 12))
    ranked = list(range(1, 26))
    last_draw = list(range(1, 16))
    portfolio = m.build_portfolio(core, ranked, n_games=5, last_draw=last_draw)
    assert "conservador" in portfolio
    assert "equilibrado" in portfolio
    assert "agressivo" in portfolio
    total = sum(len(v) for v in portfolio.values())
    assert total == 5


def test_print_portfolio_runs_without_error():
    portfolio = {
        "conservador": [[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]],
        "equilibrado": [[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 16]],
        "agressivo": [],
    }
    # Rich Console writes to stdout; just verify no exception is raised
    m.print_portfolio(portfolio, n_jogos=2, target_concurso=3675)
```

- [ ] **Step 6: Run portfolio tests**

```bash
pytest tests/test_portfolio.py -v
```

Expected: all tests pass

- [ ] **Step 7: Commit**

```bash
git add src/cli/portfolio.py tests/test_portfolio.py tests/test_cli_smoke.py
git commit -m "feat(cli): add portfolio command (absorb predict_portfolio.py logic)"
```

---

## Task 7: Implement `src/cli/lab.py`

**Files:**
- Create: `src/cli/lab.py`

- [ ] **Step 1: Add smoke test**

```python
# Append to tests/test_cli_smoke.py

def test_lab_help():
    from cli.app import app
    runner = CliRunner()
    result = runner.invoke(app, ["lab", "--help"])
    assert result.exit_code == 0
    assert "backfill-clima" in result.output
    assert "lunar-check" in result.output
    assert "ablation" in result.output
```

- [ ] **Step 2: Run failing test**

```bash
pytest tests/test_cli_smoke.py::test_lab_help -v
```

Expected: error about missing `cli.lab`

- [ ] **Step 3: Create `src/cli/lab.py`**

```python
"""lab subcommands — re-exposes lotofacil_lab Typer app."""
from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from lotofacil_lab.main import app
```

- [ ] **Step 4: Run test**

```bash
pytest tests/test_cli_smoke.py::test_lab_help -v
```

Expected: PASSED

- [ ] **Step 5: Commit**

```bash
git add src/cli/lab.py tests/test_cli_smoke.py
git commit -m "feat(cli): add lab subgroup (re-exposes lotofacil_lab commands)"
```

---

## Task 8: Update `pyproject.toml` entry point

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Update entry point**

Change line:
```toml
lotofacil = "src.main:app"
```
To:
```toml
lotofacil = "src.cli.app:app"
```

- [ ] **Step 2: Reinstall package**

```bash
pip install -e . --quiet
```

- [ ] **Step 3: Verify CLI works**

```bash
lotofacil --help
```

Expected output contains: `prever`, `dados`, `modelo`, `portfolio`, `lab`

```bash
lotofacil dados --help
lotofacil modelo --help
lotofacil portfolio --help
lotofacil lab --help
```

Expected: all return exit code 0 with correct commands listed.

- [ ] **Step 4: Run all tests**

```bash
pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml
git commit -m "feat(cli): update pyproject.toml entry point to src.cli.app:app"
```

---

## Task 9: Update `README.md`

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Replace the Quick Start / Commands section**

Find the existing Quick Start or commands section and replace with:

```markdown
## Instalação

```bash
git clone https://github.com/andredfaria/loteria.git
cd loteria/lotofacil
python -m venv venv && source venv/bin/activate
pip install -e .
```

## Uso rápido

```bash
# Dados
lotofacil dados atualizar --all   # importa histórico completo de dados/
lotofacil dados atualizar         # sincroniza novos sorteios da API
lotofacil dados status            # último concurso, total de draws

# Modelos
lotofacil modelo treinar          # treina ensemble (Frequency + ML + LSTM)
lotofacil modelo backtest         # walk-forward → saida/relatorio.html
lotofacil modelo historico        # histórico de predições
lotofacil modelo validar          # valida predições contra resultados reais

# Predição
lotofacil prever                  # prediz 11 números (cascade: neural → ensemble)
lotofacil prever --approach ml    # força abordagem específica

# Portfólio
lotofacil portfolio               # gera portfólio para o próximo concurso
lotofacil portfolio --jogos 8     # portfólio com 8 jogos
lotofacil portfolio --concurso N  # concurso específico
lotofacil portfolio validar N     # valida portfólio gerado para concurso N

# Experimentos (clima + lua + ablação)
lotofacil lab backfill-clima      # preenche histórico climático (Open-Meteo)
lotofacil lab lunar-check --data YYYY-MM-DD
lotofacil lab ablation            # ablation study completo
lotofacil lab treinar --config base+clima+lua
```
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: update README with unified CLI commands"
```

---

## Task 10: Final integration verification

- [ ] **Step 1: Run full test suite**

```bash
pytest tests/ src/lotofacil_lab/tests/ -v 2>&1 | tail -30
```

Expected: all tests pass (or same baseline as before the refactor).

- [ ] **Step 2: Verify CLI end-to-end help**

```bash
lotofacil --help
lotofacil dados --help
lotofacil modelo --help
lotofacil prever --help
lotofacil portfolio --help
lotofacil portfolio validar --help
lotofacil lab --help
lotofacil lab lunar-check --help
```

All must return exit code 0.

- [ ] **Step 3: Verify legacy/ is clean**

```bash
ls legacy/
```

Expected: `analise/  coleta/  dashboard/  estrategia/  geracao/  portfolio/  README.md  scripts/  sugestao/  validacao/`

- [ ] **Step 4: Verify root is clean**

```bash
ls *.py
```

Expected: only `conftest.py` (all other scripts moved to `legacy/scripts/`).

- [ ] **Step 5: Verify .gitignore is working**

```bash
git status
```

Untracked `dados/clima/` files and `saida/` should NOT appear.

- [ ] **Step 6: Final commit**

```bash
git add -A
git status  # review before commit
git commit -m "chore: final cleanup and integration verification"
```
