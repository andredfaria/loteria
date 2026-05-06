"""CLI entry point for the lotofacil_lab experimental pipeline.

Usage:
    python -m lotofacil_lab.main backfill-clima --ultimos 500
    python -m lotofacil_lab.main lunar-check --data 2025-12-04
    python -m lotofacil_lab.main train --config base+temp+priors --epochs 30
    python -m lotofacil_lab.main predict --config base+temp+priors
    python -m lotofacil_lab.main ablation --n-test 100 --retrain-every 50
    python -m lotofacil_lab.main compare --periodo 2024-04 --configs random,freq,base
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table
from rich import box

# Ensure src/ is in sys.path before any local imports
_SRC = Path(__file__).resolve().parent.parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from lotofacil_lab.config import OUTPUT_DIR  # noqa: E402

app = typer.Typer(
    name="lotofacil-lab",
    help="Experimental ML pipeline for Lotofácil — climate, lunar & strategy features.",
    add_completion=False,
)
console = Console()


def _setup_logging(debug: bool) -> None:
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        level=level,
    )


# ── backfill-clima ─────────────────────────────────────────────────────────────

@app.command("backfill-clima")
def backfill_clima(
    ultimos: int = typer.Option(None, help="Fetch only the N most recent draws."),
    from_c: int = typer.Option(1, "--from", help="First concurso."),
    to_c: int = typer.Option(None, "--to", help="Last concurso."),
    force: bool = typer.Option(False, "--force", help="Re-fetch even if file exists."),
    debug: bool = typer.Option(False, "--debug"),
) -> None:
    """Backfill historical climate data via Open-Meteo Archive API."""
    _setup_logging(debug)
    from lotofacil_lab.coleta.backfill_clima_archive import backfill
    count = backfill(concurso_from=from_c, concurso_to=to_c, ultimos=ultimos, force=force)
    console.print(f"[green]Done:[/green] {count} draws fetched.")


# ── lunar-check ───────────────────────────────────────────────────────────────

@app.command("lunar-check")
def lunar_check(
    data: str = typer.Option(..., "--data", help="Date YYYY-MM-DD"),
    debug: bool = typer.Option(False, "--debug"),
) -> None:
    """Print lunar features for a given date (smoke test)."""
    _setup_logging(debug)
    from lotofacil_lab.data.lunar_loader import get_lunar_features_dict, LUNAR_FEATURE_NAMES
    features = get_lunar_features_dict(data)
    table = Table(title=f"Lunar features — {data}", box=box.SIMPLE)
    table.add_column("Feature")
    table.add_column("Value", justify="right")
    for k, v in features.items():
        table.add_row(k, f"{v:.4f}")
    console.print(table)


# ── train ──────────────────────────────────────────────────────────────────────

@app.command("train")
def train(
    config_sig: str = typer.Option("base+temp+priors", "--config",
                                    help="Feature config signature. e.g. 'base+temp+priors+clima+lua'"),
    epochs: int = typer.Option(None, "--epochs", help="Override max epochs."),
    n_draws: int = typer.Option(None, "--n-draws", help="Use only last N draws."),
    debug: bool = typer.Option(False, "--debug"),
) -> None:
    """Train a NeuralModular model for the given feature config and save it."""
    _setup_logging(debug)
    import lotofacil_lab.config as lab_cfg
    from lotofacil_lab.data.feature_flags import FeatureConfig
    from lotofacil_lab.data.draws_loader import load_draws, load_draws_last_n
    from lotofacil_lab.models.neural_modular import NeuralModular

    cfg = FeatureConfig.from_signature(config_sig)
    console.print(f"Config: [cyan]{cfg.signature()}[/cyan]")

    draws = load_draws_last_n(n_draws) if n_draws else load_draws()
    console.print(f"Draws: {len(draws)} ({draws[0].concurso}–{draws[-1].concurso})")

    if epochs:
        lab_cfg.LSTM_EPOCHS = epochs

    model = NeuralModular(cfg)
    console.print("Training... (this may take a while)")
    model.fit(draws)
    model.save()
    console.print(f"[green]Saved:[/green] saved_models/neural_{cfg.signature()}.keras")


# ── predict ────────────────────────────────────────────────────────────────────

@app.command("predict")
def predict(
    config_sig: str = typer.Option("base+temp+priors", "--config"),
    n_draws: int = typer.Option(500, "--n-draws", help="Historical draws for inference context."),
    debug: bool = typer.Option(False, "--debug"),
) -> None:
    """Predict the next draw's 15 dezenas using a trained model."""
    _setup_logging(debug)
    from lotofacil_lab.data.feature_flags import FeatureConfig
    from lotofacil_lab.data.draws_loader import load_draws_last_n
    from lotofacil_lab.models.neural_modular import NeuralModular

    cfg = FeatureConfig.from_signature(config_sig)
    draws = load_draws_last_n(n_draws)
    model = NeuralModular(cfg)
    model.load()
    dezenas = model.predict(draws)
    console.print(f"[bold]Predicted dezenas[/bold] (config={cfg.signature()}):")
    console.print(" ".join(f"{d:02d}" for d in dezenas))
    console.print(f"Sum: {sum(dezenas)} | Pares: {sum(1 for d in dezenas if d % 2 == 0)}")


# ── ablation ───────────────────────────────────────────────────────────────────

@app.command("ablation")
def ablation(
    n_test: int = typer.Option(100, "--n-test", help="Test window size."),
    retrain_every: int = typer.Option(50, "--retrain-every",
                                       help="Retrain model every N steps."),
    n_draws: int = typer.Option(None, "--n-draws", help="Cap total draws loaded."),
    skip_neural: bool = typer.Option(False, "--skip-neural", help="Run only baselines."),
    debug: bool = typer.Option(False, "--debug"),
) -> None:
    """Run full ablation study: random/freq baselines + neural configs. Generates report."""
    _setup_logging(debug)
    from lotofacil_lab.data.draws_loader import load_draws, load_draws_last_n
    from lotofacil_lab.experiments.runner import ExperimentRunner
    from lotofacil_lab.experiments.report import generate_report

    draws = load_draws_last_n(n_draws) if n_draws else load_draws()
    console.print(f"Loaded {len(draws)} draws. Running ablation (n_test={n_test})...")

    runner = ExperimentRunner(draws)
    result = runner.run(n_test=n_test, retrain_every=retrain_every, run_neural=not skip_neural)

    out_path = generate_report(result)
    _print_summary_table(result["results"])
    console.print(f"\n[green]Report written to:[/green] {out_path}")


# ── compare ────────────────────────────────────────────────────────────────────

@app.command("compare")
def compare(
    periodo: str = typer.Option(None, "--periodo",
                                 help="Month filter: YYYY-MM (e.g. 2024-04)."),
    configs_str: str = typer.Option("random,freq,base", "--configs",
                                     help="Comma-separated config signatures."),
    n_test: int = typer.Option(50, "--n-test"),
    retrain_every: int = typer.Option(25, "--retrain-every"),
    debug: bool = typer.Option(False, "--debug"),
) -> None:
    """Compare specific configs in a given period. Faster than full ablation."""
    _setup_logging(debug)
    from datetime import datetime
    from lotofacil_lab.data.draws_loader import load_draws
    from lotofacil_lab.data.feature_flags import FeatureConfig
    from lotofacil_lab.experiments.runner import ExperimentRunner
    from lotofacil_lab.experiments.report import generate_report

    draws = load_draws()

    # Filter by period (YYYY-MM)
    period_start = period_end = None
    if periodo:
        try:
            year, month = int(periodo[:4]), int(periodo[5:7])
            # Find concurso range for that month
            from calendar import monthrange
            last_day = monthrange(year, month)[1]
            from datetime import datetime as dt
            period_draws = [
                d for d in draws
                if dt.strptime(d.data.replace("/", "-") if "/" in d.data else d.data, "%d-%m-%Y"
                               if "/" in d.data else "%Y-%m-%d").year == year
                and dt.strptime(d.data.replace("/", "-") if "/" in d.data else d.data, "%d-%m-%Y"
                                if "/" in d.data else "%Y-%m-%d").month == month
            ]
            if period_draws:
                period_start = period_draws[0].concurso
                period_end = period_draws[-1].concurso
                console.print(f"Period: concurso {period_start}–{period_end} ({periodo})")
        except (ValueError, IndexError) as e:
            console.print(f"[yellow]Period parse error: {e}. Using all draws.[/yellow]")

    # Parse config list
    selected_configs = []
    for sig in configs_str.split(","):
        sig = sig.strip()
        if sig in ("random", "freq", "frequency"):
            continue  # baselines always included
        try:
            selected_configs.append(FeatureConfig.from_signature(sig))
        except Exception as e:
            console.print(f"[yellow]Skipping unknown config '{sig}': {e}[/yellow]")

    runner = ExperimentRunner(draws)
    result = runner.run(
        n_test=n_test,
        retrain_every=retrain_every,
        configs=selected_configs if selected_configs else None,
        run_neural=bool(selected_configs),
        period_start=period_start,
        period_end=period_end,
    )

    out_path = generate_report(result)
    _print_summary_table(result["results"])
    console.print(f"\n[green]Report:[/green] {out_path}")


# ── helpers ────────────────────────────────────────────────────────────────────

def _print_summary_table(results: list) -> None:
    table = Table(title="Resultados", box=box.SIMPLE_HEAVY)
    table.add_column("Config", style="cyan")
    table.add_column("Acertos médios", justify="right")
    table.add_column("ROI %", justify="right")
    table.add_column("Sharpe", justify="right")
    table.add_column("p-value", justify="right")

    for entry in results:
        if "error" in entry:
            table.add_row(entry.get("name", "?"), "ERRO", "—", "—", "—")
            continue
        p = entry.get("p_value_vs_random", 1.0)
        p_str = f"[green]{p:.4f}[/green]" if p < 0.05 else f"{p:.4f}"
        table.add_row(
            entry.get("name", "?"),
            f"{entry.get('mean_hits', 0):.4f}",
            f"{entry.get('roi_pct', 0):.2f}%",
            f"{entry.get('sharpe', 0):.4f}",
            p_str,
        )
    console.print(table)


if __name__ == "__main__":
    app()
