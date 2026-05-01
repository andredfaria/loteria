"""Validate 15-number neural model performance on historical draws.

Tests the hypothesis: selecting 15 numbers via neural + filters
yields >= 11 hits at a high rate.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import numpy as np
from rich.console import Console
from rich.table import Table
from core.models import Draw
from data.loader import load_draws
from core.lottery import contar_acertos

console = Console()


def validate_neural_15(draws: list[Draw], test_window: int = 50, train_window: int = 300,
                      filtered: bool = False) -> dict:
    """Walk-forward validation of the 15-number neural model."""
    from strategies.quinze_numbers.approaches.neural import NeuralApproach

    n = len(draws)
    start_idx = n - test_window - train_window

    if start_idx < 0:
        console.print(f"[red]Need {train_window + test_window} draws, got {n}[/red]")
        return {}

    results = []
    hits_list = []

    console.print(f"[bold]Validating 15-number neural model on {test_window} draws...[/bold]")
    console.print(f"Training window: {train_window} draws each step")

    for i in range(test_window):
        idx = start_idx + i + train_window
        train_draws = draws[idx - train_window:idx]
        actual_draw = draws[idx]

        try:
            neural = NeuralApproach()
            neural.fit(train_draws)

            if filtered:
                top15 = neural.predict_with_filters(train_draws)
            else:
                probas = neural.predict_proba()
                top15 = sorted(np.argsort(probas)[::-1][:15] + 1)

            hits = contar_acertos(top15, actual_draw.dezenas)
            hits_list.append(hits)

            results.append({
                "concurso": actual_draw.concurso,
                "hits": hits,
                "predicted": top15,
                "actual": actual_draw.dezenas,
            })

            status = "[green]✓[/green]" if hits >= 11 else "[red]✗[/red]"
            console.print(f"  Concurso {actual_draw.concurso}: {hits}/15 hits {status}")

        except Exception as e:
            console.print(f"  [yellow]Failed concurso {actual_draw.concurso}: {e}[/yellow]")

    if not hits_list:
        return {"error": "No valid results"}

    return {
        "total": len(hits_list),
        "mean_hits": float(np.mean(hits_list)),
        "median_hits": float(np.median(hits_list)),
        "hit_11_plus": sum(1 for h in hits_list if h >= 11),
        "hit_12_plus": sum(1 for h in hits_list if h >= 12),
        "hit_13_plus": sum(1 for h in hits_list if h >= 13),
        "hit_14_plus": sum(1 for h in hits_list if h >= 14),
        "hit_15": sum(1 for h in hits_list if h == 15),
        "hit_rate_11": sum(1 for h in hits_list if h >= 11) / len(hits_list),
        "hit_rate_12": sum(1 for h in hits_list if h >= 12) / len(hits_list),
        "hit_rate_13": sum(1 for h in hits_list if h >= 13) / len(hits_list),
        "best_hit": max(hits_list),
        "worst_hit": min(hits_list),
        "results": results,
    }


def validate_neural_15_loaded(draws: list[Draw], test_window: int = 50,
                               filtered: bool = False) -> dict:
    """Validate using a pre-trained 15-number neural model (no retraining)."""
    from strategies.quinze_numbers.approaches.neural import NeuralApproach

    n = len(draws)
    results = []
    hits_list = []

    console.print(f"[bold]Validating loaded 15-number neural model on last {test_window} draws...[/bold]")

    neural = NeuralApproach()
    neural.load()

    for i in range(test_window, 0, -1):
        idx = n - i
        train_draws = draws[:idx]
        actual_draw = draws[idx]

        try:
            if filtered:
                top15 = neural.predict_with_filters(train_draws)
            else:
                probas = neural.predict_proba(train_draws)
                top15 = sorted(np.argsort(probas)[::-1][:15] + 1)
            hits = contar_acertos(top15, actual_draw.dezenas)
            hits_list.append(hits)

            results.append({
                "concurso": actual_draw.concurso,
                "hits": hits,
                "predicted": top15,
                "actual": actual_draw.dezenas,
            })

            status = "[green]✓[/green]" if hits >= 11 else "[red]✗[/red]"
            console.print(f"  Concurso {actual_draw.concurso}: {hits}/15 hits {status}")

        except Exception as e:
            console.print(f"  [yellow]Failed concurso {actual_draw.concurso}: {e}[/yellow]")

    if not hits_list:
        return {"error": "No valid results"}

    return {
        "total": len(hits_list),
        "mean_hits": float(np.mean(hits_list)),
        "median_hits": float(np.median(hits_list)),
        "hit_11_plus": sum(1 for h in hits_list if h >= 11),
        "hit_12_plus": sum(1 for h in hits_list if h >= 12),
        "hit_13_plus": sum(1 for h in hits_list if h >= 13),
        "hit_14_plus": sum(1 for h in hits_list if h >= 14),
        "hit_15": sum(1 for h in hits_list if h == 15),
        "hit_rate_11": sum(1 for h in hits_list if h >= 11) / len(hits_list),
        "hit_rate_12": sum(1 for h in hits_list if h >= 12) / len(hits_list),
        "hit_rate_13": sum(1 for h in hits_list if h >= 13) / len(hits_list),
        "best_hit": max(hits_list),
        "worst_hit": min(hits_list),
        "results": results,
    }


def print_results(result: dict):
    """Print validation results as a nice table."""
    if "error" in result:
        console.print(f"[red]{result['error']}[/red]")
        return

    table = Table(title="15-Number Neural Model Validation Results")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Draws Tested", str(result["total"]))
    table.add_row("Mean Hits", f"{result['mean_hits']:.2f}")
    table.add_row("Median Hits", f"{result['median_hits']:.1f}")
    table.add_row("11+ Hits", f"{result['hit_11_plus']} ({result['hit_rate_11'] * 100:.1f}%)")
    table.add_row("12+ Hits", f"{result['hit_12_plus']} ({result['hit_rate_12'] * 100:.1f}%)")
    table.add_row("13+ Hits", f"{result['hit_13_plus']} ({result['hit_rate_13'] * 100:.1f}%)")
    table.add_row("14+ Hits", f"{result['hit_14_plus']}")
    table.add_row("15 Hits", f"{result['hit_15']}")
    table.add_row("Best Hit", str(result['best_hit']))
    table.add_row("Worst Hit", str(result['worst_hit']))

    console.print(table)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Validate 15-number neural model")
    parser.add_argument("--window", "-w", type=int, default=20,
                        help="Number of draws to test (default: 20)")
    parser.add_argument("--train", "-t", type=int, default=200,
                        help="Training window size (default: 200)")
    parser.add_argument("--loaded", "-l", action="store_true",
                        help="Use pre-trained model (no retraining)")
    parser.add_argument("--filtered", action="store_true",
                        help="Apply statistical filters to predictions")
    args = parser.parse_args()

    draws = load_draws(source="db")

    if args.loaded:
        result = validate_neural_15_loaded(draws, test_window=args.window, filtered=args.filtered)
    else:
        result = validate_neural_15(draws, test_window=args.window, train_window=args.train,
                                    filtered=args.filtered)

    print_results(result)
