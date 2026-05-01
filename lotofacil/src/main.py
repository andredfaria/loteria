"""CLI entry point for Lotofácil Prediction System."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import typer
from rich.console import Console
from rich.table import Table
import numpy as np

from core.models import Draw
from data.database import DatabaseManager
from data.fetcher import LotofacilFetcher
from data.loader import load_draws
from strategies.eleven_numbers.predictor import ElevenNumbersStrategy
from evaluation.backtest import BacktestEngine
from evaluation.comparison import compare_approaches

app = typer.Typer(help="Lotofácil Prediction System v2.0", add_completion=False)
console = Console()


@app.command()
def collect(
    start: int = typer.Option(None, "--from", help="Start concurso number"),
    end: int = typer.Option(None, "--to", help="End concurso number"),
    latest: bool = typer.Option(False, "--latest", help="Fetch only latest draw"),
    sync: bool = typer.Option(False, "--sync", help="Sync new draws"),
):
    """Collect draws from API."""
    db = DatabaseManager()
    fetcher = LotofacilFetcher(db=db)

    if latest:
        console.print("[bold]Fetching latest draw...[/bold]")
        rec = fetcher.fetch_latest()
        if rec:
            console.print(f"Concurso {rec['concurso']} ({rec['data']}): {rec['dezenas']}")
    elif sync:
        console.print("[bold]Syncing new draws...[/bold]")
        count = fetcher.sync_new_draws()
        console.print(f"Synced {count} new draws")
    elif start and end:
        console.print(f"[bold]Fetching draws {start} to {end}...[/bold]")
        count = fetcher.fetch_range(start, end)
        console.print(f"Fetched {count} draws")
    else:
        console.print("Use --latest, --sync, or --from N --to M")


@app.command()
def process():
    """Process raw draws: migrate JSONs to DB, create consolidated files."""
    from scripts.process import migrate_jsons_to_db, create_all_draws_json
    console.print("[bold]Migrating JSONs to database...[/bold]")
    count = migrate_jsons_to_db()
    console.print(f"Migrated {count} draws")
    console.print("[bold]Creating all_draws.json...[/bold]")
    create_all_draws_json()
    console.print("[green]Done![/green]")


@app.command()
def predict(
    approach: str = typer.Option("all", "--approach", "-a",
                                  help="Approach: statistical, ml, neural, all"),
    filtered: bool = typer.Option(False, "--filtered", "-f",
                                   help="Apply statistical filters to prediction"),
    concurso: int = typer.Option(None, "--concurso", "-c", help="Target concurso"),
):
    """Predict numbers for the next draw."""
    draws = load_draws(source="db")
    if not draws:
        console.print("[red]No data available. Run 'collect' first.[/red]")
        return

    strategy = ElevenNumbersStrategy()
    pred = strategy.predict(draws, approach=approach)

    filtered_numbers = None
    if filtered and approach == "neural":
        from strategies.eleven_numbers.approaches.neural import NeuralApproach
        neural = NeuralApproach()
        if not neural.is_fitted:
            try:
                neural.load()
            except Exception:
                neural.fit(draws)
        filtered_numbers = neural.predict_with_filters(draws)

    console.print(f"\n[bold]Prediction for Concurso {pred.concurso_alvo}[/bold]")
    console.print(f"Strategy: {pred.strategy} | Approach: {pred.approach}")

    if filtered_numbers:
        console.print(f"\n[bold blue]Model (raw): {pred.dezenas}[/bold blue]")
        console.print(f"[bold green]Filtered (optimized): {filtered_numbers}[/bold green]")

        from core.lottery import estatisticas_dezenas
        console.print(f"\n[bold]Model stats:[/bold]")
        s = estatisticas_dezenas(pred.dezenas)
        console.print(f"  Soma: {s['soma']}, Pares: {s['pares']}, Moldura: {s['moldura']}")
        console.print(f"  Primos: {s['primos']}, Fibonacci: {s['fibonacci']}, Consec: {s['consecutivos']}")

        console.print(f"\n[bold]Filtered stats:[/bold]")
        s = estatisticas_dezenas(filtered_numbers)
        console.print(f"  Soma: {s['soma']}, Pares: {s['pares']}, Moldura: {s['moldura']}")
        console.print(f"  Primos: {s['primos']}, Fibonacci: {s['fibonacci']}, Consec: {s['consecutivos']}")
    else:
        console.print(f"\n[bold green]Numbers: {pred.dezenas}[/bold green]")
        console.print(f"Confidence: {pred.confianca_media:.4f}")


@app.command()
def backtest(
    approach: str = typer.Option("all", "--approach", "-a"),
    window: int = typer.Option(300, "--window", "-w", help="Training window size"),
):
    """Run walk-forward backtest."""
    draws = load_draws(source="db")
    if len(draws) <= window:
        console.print(f"[red]Need more than {window} draws, got {len(draws)}[/red]")
        return

    strategy = ElevenNumbersStrategy()
    engine = BacktestEngine(strategy, train_window=window)
    result = engine.run(draws)

    table = Table(title="Backtest Results")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Draws Tested", str(result.get("total_draws_tested", 0)))
    table.add_row("Mean Hits", f"{result.get('mean_hits', 0):.2f}")
    table.add_row("11+ Hits", str(result.get("hit_11_plus", 0)))
    table.add_row("12+ Hits", str(result.get("hit_12_plus", 0)))
    table.add_row("13+ Hits", str(result.get("hit_13_plus", 0)))
    table.add_row("Hit Rate 11+", f"{result.get('hit_rate_11', 0) * 100:.1f}%")
    table.add_row("ROI", f"{result.get('roi_percent', 0):.2f}%")
    table.add_row("Best Hit", str(result.get("best_hit", 0)))

    console.print(table)


@app.command()
def compare():
    """Compare all approaches side by side."""
    draws = load_draws(source="db")
    strategy = ElevenNumbersStrategy()
    comparison = compare_approaches(strategy, draws)

    table = Table(title="Approach Comparison")
    table.add_column("Approach", style="cyan")
    table.add_column("Mean Hits", style="green")
    table.add_column("11+ Hits", style="green")
    table.add_column("12+ Hits", style="green")
    table.add_column("ROI %", style="green")
    table.add_column("Best Hit", style="green")

    for name, metrics in comparison.items():
        if "error" in metrics:
            table.add_row(name, "ERROR", "ERROR", "ERROR", "ERROR", "ERROR")
        else:
            table.add_row(
                name,
                f"{metrics.get('mean_hits', 0):.2f}",
                str(metrics.get("hit_11_plus", 0)),
                str(metrics.get("hit_12_plus", 0)),
                f"{metrics.get('roi_percent', 0):.2f}",
                str(metrics.get("best_hit", 0)),
            )

    console.print(table)


@app.command()
def train_neural(
    epochs: int = typer.Option(None, "--epochs", "-e", help="Override max epochs"),
):
    """Train the neural network (LSTM + Attention) on all historical draws."""
    draws = load_draws(source="db")
    if len(draws) < 100:
        console.print("[red]Need at least 100 draws to train neural model.[/red]")
        return

    from strategies.eleven_numbers.approaches.neural import NeuralApproach
    neural = NeuralApproach()

    console.print("[bold]Training LSTM + Attention neural network...[/bold]")
    console.print(f"Draws: {len(draws)}")
    console.print("[dim]This may take several minutes...[/dim]")

    try:
        neural.fit(draws)
    except Exception as e:
        console.print(f"[red]Training failed: {e}[/red]")
        return

    probas = neural.predict_proba()
    indices = np.argsort(probas)[::-1][:11]
    numbers = sorted(int(i + 1) for i in indices)

    history = neural.get_training_history()
    if "val_loss" in history:
        best_val = min(history["val_loss"])
        console.print(f"\n[bold]Training complete![/bold]")
        console.print(f"Best val_loss: {best_val:.4f}")
        if "loss" in history:
            console.print(f"Final train_loss: {history['loss'][-1]:.4f}")

    console.print(f"\n[bold green]Top 11 predicted numbers: {numbers}[/bold green]")
    console.print(f"Approach: {neural.name}")

    neural.save()
    console.print(f"[dim]Model saved to output/models/[/dim]")


@app.command()
def validate_neural(
    window: int = typer.Option(20, "--window", "-w", help="Number of draws to test"),
    train: int = typer.Option(200, "--train", "-t", help="Training window size"),
):
    """Validate neural model on historical draws (walk-forward)."""
    draws = load_draws(source="db")

    n = len(draws)
    start_idx = n - window - train

    if start_idx < 0:
        console.print(f"[red]Need {train + window} draws, got {n}[/red]")
        return

    console.print(f"[bold]Validating neural model on {window} draws[/bold]")
    console.print(f"Training window: {train} draws each step")
    console.print(f"[dim]This will take several minutes...[/dim]")

    hits_list = []
    for i in range(window):
        idx = start_idx + i + train
        train_draws = draws[idx - train:idx]
        actual_draw = draws[idx]

        try:
            from strategies.eleven_numbers.approaches.neural import NeuralApproach
            neural = NeuralApproach()
            neural.fit(train_draws)
            probas = neural.predict_proba()
            top11 = sorted(np.argsort(probas)[::-1][:11] + 1)
            hits = len(set(top11) & set(actual_draw.dezenas))
            hits_list.append(hits)

            status = "[green]✓[/green]" if hits >= 11 else "[red]✗[/red]"
            console.print(f"  Concurso {actual_draw.concurso}: {hits}/11 hits {status}")
        except Exception as e:
            console.print(f"  [yellow]Failed concurso {actual_draw.concurso}: {e}[/yellow]")

    if not hits_list:
        console.print("[red]No valid results[/red]")
        return

    table = Table(title="Neural Model Validation Results")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Draws Tested", str(len(hits_list)))
    table.add_row("Mean Hits", f"{np.mean(hits_list):.2f}")
    table.add_row("Median Hits", f"{np.median(hits_list):.1f}")
    table.add_row("11+ Hits", f"{sum(1 for h in hits_list if h >= 11)} ({sum(1 for h in hits_list if h >= 11) / len(hits_list) * 100:.1f}%)")
    table.add_row("12+ Hits", f"{sum(1 for h in hits_list if h >= 12)}")
    table.add_row("13+ Hits", f"{sum(1 for h in hits_list if h >= 13)}")
    table.add_row("Best Hit", str(max(hits_list)))
    table.add_row("Worst Hit", str(min(hits_list)))

    console.print(table)


@app.command()
def predict_15(
    filtered: bool = typer.Option(True, "--filtered/-nf", help="Apply statistical filters (default: on)"),
    loaded: bool = typer.Option(False, "--loaded", "-l", help="Use pre-trained model (no retraining)"),
):
    """Predict 15 numbers calibrated to hit 11+."""
    draws = load_draws(source="db")
    if not draws:
        console.print("[red]No data available. Run 'collect' first.[/red]")
        return

    from strategies.quinze_numbers.predictor import QuinzePredictor
    predictor = QuinzePredictor()

    if loaded:
        numbers = predictor.predict_loaded(draws, use_filters=filtered)
        console.print(f"\n[bold]15-Number Prediction (pre-trained)[/bold]")
    else:
        console.print("[bold]Training model for 15-number prediction...[/bold]")
        console.print("[dim]This may take a minute...[/dim]")
        numbers = predictor.predict(draws, use_filters=filtered)
        console.print(f"\n[bold]15-Number Prediction (fresh training)[/bold]")

    console.print(f"[bold green]Numbers: {sorted(numbers)}[/bold green]")

    from core.lottery import estatisticas_dezenas
    s = estatisticas_dezenas(numbers)
    console.print(f"\n[bold]Stats:[/bold]")
    console.print(f"  Soma: {s['soma']}, Pares: {s['pares']}, Ímpares: {15 - s['pares']}")
    console.print(f"  Moldura: {s['moldura']}, Primos: {s['primos']}")
    console.print(f"  Fibonacci: {s['fibonacci']}, Consecutivos: {s['consecutivos']}")

    last_draw = draws[-1]
    reps = len(set(numbers) & set(last_draw.dezenas))
    console.print(f"  Repetidos do anterior: {reps}")


@app.command()
def train_neural_15(
    epochs: int = typer.Option(None, "--epochs", "-e", help="Override max epochs"),
):
    """Train the 15-number neural network (LSTM + Attention)."""
    draws = load_draws(source="db")
    if len(draws) < 100:
        console.print("[red]Need at least 100 draws to train neural model.[/red]")
        return

    from strategies.quinze_numbers.approaches.neural import NeuralApproach
    neural = NeuralApproach()

    console.print("[bold]Training 15-number LSTM + Attention neural network...[/bold]")
    console.print(f"Draws: {len(draws)}")
    console.print("[dim]This may take several minutes...[/dim]")

    try:
        neural.fit(draws)
    except Exception as e:
        console.print(f"[red]Training failed: {e}[/red]")
        return

    probas = neural.predict_proba()
    indices = np.argsort(probas)[::-1][:15]
    numbers = sorted(int(i + 1) for i in indices)

    history = neural.get_training_history()
    if "val_loss" in history:
        best_val = min(history["val_loss"])
        console.print(f"\n[bold]Training complete![/bold]")
        console.print(f"Best val_loss: {best_val:.4f}")
        if "loss" in history:
            console.print(f"Final train_loss: {history['loss'][-1]:.4f}")

    console.print(f"\n[bold green]Top 15 predicted numbers: {numbers}[/bold green]")

    neural.save()
    console.print(f"[dim]Model saved to output/models/lstm_attention_15numbers.keras[/dim]")


@app.command()
def status():
    """Show database status."""
    db = DatabaseManager()
    count = db.count_concursos()
    latest = db.get_latest_concurso()

    console.print(f"[bold]Database status[/bold]")
    console.print(f"Total draws: {count}")
    if latest:
        console.print(f"Latest: Concurso {latest['concurso']} ({latest['data']})")


if __name__ == "__main__":
    app()
