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
    import logging
    logging.basicConfig(level=logging.DEBUG if debug else logging.WARNING)

    from lotofacil.infra.config import PROJETO_RAIZ
    from lotofacil.infra.dados.leitor import load_draws
    from lotofacil.infra.modelos.ensemble import EnsemblePredictor

    draws = load_draws(PROJETO_RAIZ / "dados")

    if len(draws) < 100:
        console.print("[red]Dados insuficientes. Execute: lotofacil dados atualizar --escopo todos[/red]")
        raise typer.Exit(1)

    console.print(f"[cyan]Treinando em {len(draws)} concursos...[/cyan]")
    predictor = EnsemblePredictor()
    predictor.fit(draws)
    predictor.save()
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
    logging.basicConfig(level=logging.DEBUG if debug else logging.WARNING)

    from lotofacil.infra.config import PROJETO_RAIZ as PROJECT_ROOT
    from lotofacil.infra.dados.leitor import load_draws
    from lotofacil.infra.avaliacao.backtest import BacktestEngine, BacktestSummary
    from lotofacil.infra.avaliacao.baseline import random_game
    from lotofacil.infra.modelos.frequency_model import FrequencyModel
    from lotofacil.infra.modelos.frequency_ensemble import FrequencyEnsembleModel
    from lotofacil.infra.modelos.probabilistic import ProbabilisticModel
    from lotofacil.infra.modelos.ensemble import EnsemblePredictor
    from lotofacil.infra.avaliacao.gerador_html import HTMLReportGenerator

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
    from lotofacil.infra.dados.banco import DatabaseManager

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
    from lotofacil.infra.dados.banco import DatabaseManager

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
        console.print("[yellow]Nenhuma predição pôde ser validada (sorteios não disponíveis).[/yellow]")
    else:
        console.print(f"\n[green]✓ {validated} predição(ões) validada(s)[/green]")
