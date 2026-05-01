"""CLI entry point for the Lotofácil ML system."""

import logging
import sys
import time
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

# Ensure src/ is in sys.path so `lotofacil_ml` is importable
_src_dir = Path(__file__).resolve().parent.parent
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

app = typer.Typer(name="lotofacil-ml", help="Lotofácil ML prediction system", add_completion=False)
console = Console()

# ── Shared state ───────────────────────────────────────────────────────────────

def _setup_logging(debug: bool) -> None:
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        level=level,
    )


# ── update ─────────────────────────────────────────────────────────────────────

@app.command()
def update(
    all: bool = typer.Option(False, "--all", help="Load all draws from local dados/ files"),
    latest: bool = typer.Option(False, "--latest", help="Fetch only the latest draw from API"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update local database with draw data."""
    _setup_logging(debug)
    from lotofacil_ml.data.database import DatabaseManager
    from lotofacil_ml.data.fetcher import LotofacilFetcher

    db = DatabaseManager()
    fetcher = LotofacilFetcher(db)

    if all:
        console.print("[cyan]Loading all draws from local files...[/cyan]")
        draws = fetcher.fetch_all_results()
        console.print(f"[green]✓ Database updated with {len(draws)} concursos[/green]")
    elif latest:
        console.print("[cyan]Fetching latest draw from API...[/cyan]")
        draw = fetcher.fetch_latest()
        if draw:
            console.print(f"[green]✓ Latest concurso: {draw['concurso']} ({draw['data']})[/green]")
        else:
            console.print("[red]Could not fetch latest draw[/red]")
    else:
        console.print("[cyan]Syncing new draws from API...[/cyan]")
        n = fetcher.sync_new_draws()
        console.print(f"[green]✓ Synced {n} new draws[/green]")


# ── train ──────────────────────────────────────────────────────────────────────

@app.command()
def train(
    debug: bool = typer.Option(False, "--debug"),
):
    """Train all prediction models on historical data."""
    _setup_logging(debug)
    from lotofacil_ml.data.database import DatabaseManager
    from lotofacil_ml.models.ensemble import EnsemblePredictor

    db = DatabaseManager()
    draws = db.get_all_concursos()

    if len(draws) < 100:
        console.print("[red]Insufficient data. Run `update --all` first.[/red]")
        raise typer.Exit(1)

    console.print(f"[cyan]Training on {len(draws)} concursos...[/cyan]")
    predictor = EnsemblePredictor()
    predictor.train(draws)
    console.print("[green]✓ Training complete. Models saved.[/green]")


# ── predict ────────────────────────────────────────────────────────────────────

@app.command()
def predict(
    debug: bool = typer.Option(False, "--debug"),
):
    """Generate a prediction for the next concurso."""
    _setup_logging(debug)
    from lotofacil_ml.data.database import DatabaseManager
    from lotofacil_ml.models.ensemble import EnsemblePredictor

    db = DatabaseManager()
    draws = db.get_all_concursos()

    if not draws:
        console.print("[red]No data found. Run `update --all` first.[/red]")
        raise typer.Exit(1)

    predictor = EnsemblePredictor()
    predictor.load()

    pred = predictor.predict_next_concurso(draws)

    # Save to DB
    db.save_prediction(
        pred["concurso_previsto"],
        pred["dezenas_sugeridas"],
        pred["probabilidades"],
        pred["confianca_media"],
        pred["modelos_utilizados"],
    )

    # Display
    dezenas_str = "  ".join(f"{d:02d}" for d in sorted(pred["dezenas_sugeridas"]))
    console.print()
    console.print(Panel(
        f"[bold cyan]Predição — Concurso {pred['concurso_previsto']}[/bold cyan]\n\n"
        f"[yellow]{dezenas_str}[/yellow]\n\n"
        f"Confiança média: [green]{pred['confianca_media']:.4f}[/green]\n"
        f"Modelos: [dim]{', '.join(pred['modelos_utilizados'])}[/dim]",
        box=box.DOUBLE_EDGE,
    ))

    # Top probabilities table
    table = Table(title="Probabilidades por Número", box=box.SIMPLE)
    table.add_column("Número", style="cyan", justify="center")
    table.add_column("Probabilidade", style="white", justify="right")
    table.add_column("Selecionado", justify="center")
    probs = pred["probabilidades"]
    for i, p in enumerate(probs):
        num = i + 1
        selected = "✓" if num in pred["dezenas_sugeridas"] else ""
        style = "green" if selected else ""
        table.add_row(f"{num:02d}", f"{p:.4f}", selected, style=style)
    console.print(table)


# ── validate ───────────────────────────────────────────────────────────────────

@app.command()
def validate(
    debug: bool = typer.Option(False, "--debug"),
):
    """Validate pending predictions against known results."""
    _setup_logging(debug)
    from lotofacil_ml.data.database import DatabaseManager

    db = DatabaseManager()
    pending = db.get_pending_validations()
    all_draws = {d["concurso"]: d for d in db.get_all_concursos()}

    if not pending:
        console.print("[yellow]No pending predictions to validate.[/yellow]")
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

    if validated == 0:
        console.print("[yellow]No predictions could be validated yet (draws not available).[/yellow]")
    else:
        console.print(f"\n[green]✓ {validated} prediction(s) validated[/green]")


# ── backtest ───────────────────────────────────────────────────────────────────

@app.command()
def backtest(
    dados: Path = typer.Option(None, "--dados", help="Diretório dados/"),
    start: int = typer.Option(None, "--start", help="Concurso inicial do teste"),
    end: int = typer.Option(None, "--end", help="Concurso final do teste"),
    train_window: int = typer.Option(300, "--train-window"),
    retrain_every: int = typer.Option(50, "--retrain-every"),
    models_arg: str = typer.Option("frequency,frequency_ensemble,probabilistic,ensemble", "--models",
                                    help="Modelos separados por vírgula: frequency,frequency_ensemble,ml,probabilistic,ensemble"),
    cost: float = typer.Option(3.00, "--cost"),
    prize_11: float = typer.Option(7.00, "--prize-11"),
    prize_12: float = typer.Option(14.00, "--prize-12"),
    prize_13: float = typer.Option(35.00, "--prize-13"),
    prize_14: float = typer.Option(2000.00, "--prize-14"),
    prize_15: float = typer.Option(1_500_000.00, "--prize-15"),
    out: Path = typer.Option(Path("saida/relatorio.html"), "--out"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Run walk-forward backtest and generate HTML report."""
    _setup_logging(debug)
    from lotofacil_ml.config import PROJECT_ROOT
    from lotofacil_ml.data.loader import load_draws
    from lotofacil_ml.backtest.engine import BacktestEngine, BacktestSummary
    from lotofacil_ml.backtest.baseline import random_game
    from lotofacil_ml.models.frequency_model import FrequencyModel
    from lotofacil_ml.models.frequency_ensemble import FrequencyEnsembleModel
    from lotofacil_ml.models.ml_model import MLEnsembleModel
    from lotofacil_ml.models.probabilistic import ProbabilisticModel
    from lotofacil_ml.models.ensemble import EnsemblePredictor
    from lotofacil_ml.report.html_generator import HTMLReportGenerator

    dados_dir = dados or PROJECT_ROOT / "dados"
    prize_table = {11: prize_11, 12: prize_12, 13: prize_13, 14: prize_14, 15: prize_15}

    console.print(f"[cyan]Carregando histórico de {dados_dir}...[/cyan]")
    draws = load_draws(dados_dir)
    if len(draws) < 200:
        console.print(f"[red]Dados insuficientes: {len(draws)} concursos. Mínimo: 200.[/red]")
        raise typer.Exit(1)
    console.print(f"[green]✓ {len(draws)} concursos carregados[/green]")

    concurso_nums = [d.concurso for d in draws]
    if start and start in concurso_nums:
        start_idx = concurso_nums.index(start)
    else:
        # Test the last 500 draws by default (respects train_window minimum)
        start_idx = max(train_window, len(draws) - 500)
    end_idx = (concurso_nums.index(end) + 1 if end and end in concurso_nums else len(draws))

    model_map = {
        "frequency": FrequencyModel,
        "frequency_ensemble": FrequencyEnsembleModel,
        "ml": MLEnsembleModel,
        "probabilistic": ProbabilisticModel,
        "ensemble": EnsemblePredictor,
    }
    selected_names = [m.strip() for m in models_arg.split(",") if m.strip() in model_map]
    if not selected_names:
        console.print("[red]Nenhum modelo válido selecionado.[/red]")
        raise typer.Exit(1)

    summaries = {}
    baseline_results = []

    for name in selected_names:
        console.print(f"[cyan]Rodando backtest: {name}...[/cyan]")
        model = model_map[name]()
        engine = BacktestEngine(model, train_window=train_window, retrain_every=retrain_every)
        results = engine.run(draws, start_idx=start_idx, end_idx=end_idx)
        summaries[name] = BacktestSummary(model_name=name, results=results)
        console.print(f"  [green]✓ {name}: {len(results)} concursos | média acertos: {summaries[name].mean_hits:.3f}[/green]")

        if not baseline_results:
            for r in results:
                idx = concurso_nums.index(r.concurso)
                rg = random_game()
                hits = len(set(rg) & set(draws[idx].dezenas))
                baseline_results.append(type("BR", (), {"hits": hits, "concurso": r.concurso})())

    console.print("[cyan]Gerando relatório HTML...[/cyan]")
    gen = HTMLReportGenerator(cost=cost, prize_table=prize_table)
    gen.generate(summaries, baseline_results, out)
    console.print(f"[green]✓ Relatório salvo em: {out}[/green]")


# ── report ─────────────────────────────────────────────────────────────────────

@app.command()
def report(
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Export report to file"),
    n: int = typer.Option(50, "--n", help="Number of draws for quick backtest"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Generate a performance report."""
    _setup_logging(debug)
    from lotofacil_ml.data.database import DatabaseManager
    from lotofacil_ml.evaluation.metrics import LotofacilMetrics
    from lotofacil_ml.evaluation.report import ReportGenerator
    from lotofacil_ml.evaluation.validator import WalkForwardValidator

    db = DatabaseManager()
    draws = db.get_all_concursos()
    validator = WalkForwardValidator(draws)
    results = validator.walk_forward_validation(n_last=n)

    reporter = ReportGenerator()
    reporter.generate_terminal_report(results)

    if output:
        reporter.export_txt_report(results, output)
        console.print(f"[green]Report saved to {output}[/green]")


# ── schedule ───────────────────────────────────────────────────────────────────

@app.command()
def schedule(
    start: bool = typer.Option(False, "--start", help="Start the background scheduler"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Manage the automated scheduler."""
    _setup_logging(debug)
    if not start:
        console.print("Use [cyan]--start[/cyan] to start the scheduler.")
        return

    from lotofacil_ml.scheduler.updater import LotofacilScheduler

    scheduler = LotofacilScheduler()
    scheduler.start()
    console.print("[green]Scheduler started. Press Ctrl+C to stop.[/green]")
    for job in scheduler.list_jobs():
        console.print(f"  [cyan]{job['name']}[/cyan] | next: {job['next_run']}")
    try:
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.stop()
        console.print("\n[yellow]Scheduler stopped.[/yellow]")


# ── history ────────────────────────────────────────────────────────────────────

@app.command()
def history(
    limit: int = typer.Option(20, "--limit", "-l", help="Number of records to show"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Show prediction history."""
    _setup_logging(debug)
    from lotofacil_ml.data.database import DatabaseManager

    db = DatabaseManager()
    records = db.get_prediction_history(limit=limit)

    if not records:
        console.print("[yellow]No prediction history found.[/yellow]")
        return

    table = Table(title=f"Histórico de Predições (últimas {limit})", box=box.SIMPLE_HEAVY)
    table.add_column("Concurso", style="cyan", justify="center")
    table.add_column("Dezenas Sugeridas", style="white")
    table.add_column("Confiança", justify="right")
    table.add_column("Acertos", justify="center")
    table.add_column("Criado em", style="dim")

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


# ── suggest ────────────────────────────────────────────────────────────────────

@app.command()
def suggest(
    dados: Path = typer.Option(None, "--dados"),
    model_name: str = typer.Option("ensemble", "--model"),
    out: Path = typer.Option(None, "--out"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Generate a game suggestion for the next concurso."""
    _setup_logging(debug)
    import json
    from lotofacil_ml.config import PROJECT_ROOT
    from lotofacil_ml.data.loader import load_draws
    from lotofacil_ml.models.frequency_model import FrequencyModel
    from lotofacil_ml.models.ml_model import MLEnsembleModel
    from lotofacil_ml.models.probabilistic import ProbabilisticModel
    from lotofacil_ml.models.ensemble import EnsemblePredictor

    dados_dir = dados or PROJECT_ROOT / "dados"
    draws = load_draws(dados_dir)
    if not draws:
        console.print("[red]Nenhum dado encontrado.[/red]")
        raise typer.Exit(1)

    model_map = {"frequency": FrequencyModel, "ml": MLEnsembleModel,
                 "probabilistic": ProbabilisticModel, "ensemble": EnsemblePredictor}
    model_cls = model_map.get(model_name, EnsemblePredictor)
    model = model_cls()

    console.print(f"[cyan]Treinando {model_name} em {len(draws)} concursos...[/cyan]")
    model.fit(draws)

    top15 = model.select_top_15()
    next_concurso = draws[-1].concurso + 1
    dezenas_str = "  ".join(f"{n:02d}" for n in top15)

    console.print()
    console.print(f"[bold cyan]Sugestão — Concurso {next_concurso}[/bold cyan]")
    console.print(f"[yellow]{dezenas_str}[/yellow]")

    result = {"concurso": next_concurso, "modelo": model_name, "dezenas": top15}
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, indent=2, ensure_ascii=False))
        console.print(f"[green]✓ Salvo em: {out}[/green]")


if __name__ == "__main__":
    app()
