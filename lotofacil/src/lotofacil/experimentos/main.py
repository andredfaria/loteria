"""CLI entry point for the lotofacil_lab experimental pipeline.

Usage:
    python -m lotofacil_lab.main backfill-clima --ultimos 500
    python -m lotofacil_lab.main lunar-check --data 2025-12-04
    python -m lotofacil_lab.main train --config base+temp+priors --epochs 30
    python -m lotofacil_lab.main predict --config base+temp+priors
    python -m lotofacil_lab.main ablation --n-test 100 --retrain-every 50
    python -m lotofacil_lab.main compare --periodo 2024-04 --configs random,freq,base
    python -m lotofacil_lab.main today
    python -m lotofacil_lab.main similar --concurso 3683
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

from lotofacil.experimentos.config import OUTPUT_DIR  # noqa: E402

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
    from lotofacil.experimentos.coleta.backfill_clima_archive import backfill
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
    from lotofacil.experimentos.data.lunar_loader import get_lunar_features_dict, LUNAR_FEATURE_NAMES
    features = get_lunar_features_dict(data)
    table = Table(title=f"Lunar features — {data}", box=box.SIMPLE)
    table.add_column("Feature")
    table.add_column("Value", justify="right")
    for k, v in features.items():
        table.add_row(k, f"{v:.4f}")
    console.print(table)


# ── backfill-lua ───────────────────────────────────────────────────────────────

@app.command("backfill-lua")
def backfill_lua(
    ultimos: int = typer.Option(None, help="Only last N draws."),
    from_c: int = typer.Option(None, "--from", help="First concurso."),
    to_c: int = typer.Option(None, "--to", help="Last concurso."),
    debug: bool = typer.Option(False, "--debug"),
) -> None:
    """Backfill lunar cache for all/selected historical draws."""
    _setup_logging(debug)
    from lotofacil.experimentos.data.draws_loader import load_draws, load_draws_last_n
    from lotofacil.experimentos.data.lunar_loader import compute_lunar_features, _parse_iso

    draws = load_draws()
    if ultimos:
        draws = draws[-ultimos:]
    if from_c:
        draws = [d for d in draws if d.concurso >= from_c]
    if to_c:
        draws = [d for d in draws if d.concurso <= to_c]

    cached = 0
    computed = 0
    errors = 0
    with console.status("[bold green]Backfilling lunar data..."):
        for draw in draws:
            iso = _parse_iso(draw.data)
            if not iso:
                errors += 1
                continue
            arr = compute_lunar_features(iso)
            if arr.sum() == 0 and not any(e in iso for e in ["1900", "error"]):
                errors += 1
            computed += 1

    console.print(f"[green]Done:[/green] {computed} dates cached, {errors} errors.")


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
    import lotofacil.experimentos.config as lab_cfg
    from lotofacil.experimentos.data.feature_flags import FeatureConfig
    from lotofacil.experimentos.data.draws_loader import load_draws, load_draws_last_n
    from lotofacil.experimentos.models.neural_modular import NeuralModular

    cfg = FeatureConfig.from_signature(config_sig)
    console.print(f"Config: [cyan]{cfg.signature()}[/cyan]")

    draws = load_draws_last_n(n_draws) if n_draws else load_draws()
    if draws:
        console.print(f"Draws: {len(draws)} ({draws[0].concurso}–{draws[-1].concurso})")
    else:
        console.print("Draws: 0 (no data loaded)")

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
    """Predict the next draw's 15 dezenas using a trained model and save to saida/jogos/."""
    _setup_logging(debug)
    import json
    from lotofacil.experimentos.config import PROJECT_ROOT
    from lotofacil.experimentos.data.feature_flags import FeatureConfig
    from lotofacil.experimentos.data.draws_loader import load_draws_last_n
    from lotofacil.experimentos.models.neural_modular import NeuralModular

    cfg = FeatureConfig.from_signature(config_sig)
    draws = load_draws_last_n(n_draws)
    if not draws:
        console.print("[red]Sem dados. Execute: lotofacil dados atualizar --all[/red]")
        raise typer.Exit(1)

    model = NeuralModular(cfg)
    model.load()
    dezenas = model.predict(draws)

    next_concurso = draws[-1].concurso + 1
    config_slug = cfg.signature().replace("+", "-")
    abordagem = f"lab_{config_slug}"

    console.print(f"[bold]Predição — Concurso {next_concurso}[/bold] (config={cfg.signature()}):")
    console.print(" ".join(f"{d:02d}" for d in dezenas))
    console.print(f"Soma: {sum(dezenas)} | Pares: {sum(1 for d in dezenas if d % 2 == 0)}")

    saida = PROJECT_ROOT / "saida" / "jogos"
    saida.mkdir(parents=True, exist_ok=True)
    out = saida / f"predicao_{abordagem}_{next_concurso}.json"
    out.write_text(
        json.dumps({
            "concurso": next_concurso,
            "abordagem": abordagem,
            "dezenas": dezenas,
            "confianca": None,
            "config": cfg.signature(),
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    console.print(f"  [dim]💾 Salvo em saida/jogos/{out.name}[/dim]")


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
    from lotofacil.experimentos.data.draws_loader import load_draws, load_draws_last_n
    from lotofacil.experimentos.experiments.runner import ExperimentRunner
    from lotofacil.experimentos.experiments.report import generate_report

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
    from lotofacil.experimentos.data.draws_loader import load_draws
    from lotofacil.experimentos.data.feature_flags import FeatureConfig
    from lotofacil.experimentos.experiments.runner import ExperimentRunner
    from lotofacil.experimentos.experiments.report import generate_report

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


# ── today (lua + clima) ──────────────────────────────────────────────────────────

@app.command("today")
def today(
    debug: bool = typer.Option(False, "--debug"),
) -> None:
    """Show today's moon phase and climate in São Paulo."""
    _setup_logging(debug)
    from datetime import date as dt_date
    from lotofacil.experimentos.features.similarity import get_target_moon, get_target_climate
    from lotofacil.experimentos.data.lunar_loader import LUNAR_FEATURE_NAMES
    from lotofacil.experimentos.data.climate_loader import CLIMATE_FEATURE_NAMES

    hoje = dt_date.today().isoformat()

    moon = get_target_moon(hoje)
    clim = get_target_climate(hoje)

    table_moon = Table(title=f"🌙 Lua — {hoje}", box=box.SIMPLE)
    table_moon.add_column("Feature")
    table_moon.add_column("Value", justify="right")
    for k, v in zip(LUNAR_FEATURE_NAMES, moon.tolist()):
        table_moon.add_row(k, f"{v:.4f}")
    console.print(table_moon)

    table_clim = Table(title=f"☀️  Clima SP — {hoje}", box=box.SIMPLE)
    table_clim.add_column("Feature")
    table_clim.add_column("Value", justify="right")
    for k, v in zip(CLIMATE_FEATURE_NAMES, clim.tolist()):
        table_clim.add_row(k, f"{v:.4f}")
    console.print(table_clim)


# ── similar (lua+clima + padroes21) ──────────────────────────────────────────────

@app.command("similar")
def similar(
    concurso: int = typer.Option(0, "--concurso", help="Target concurso number (0 = auto next)."),
    data: str = typer.Option("", "--data", help="Target date YYYY-MM-DD (default: today)."),
    top_n: int = typer.Option(10, "--top-n", help="Number of similar draws to consider."),
    peso_similar: float = typer.Option(0.5, "--peso-similar", help="Weight for similarity score."),
    peso_padroes21: float = typer.Option(0.5, "--peso-padroes21", help="Weight for padrões-21 score."),
    debug: bool = typer.Option(False, "--debug"),
) -> None:
    """Generate a game based on moon+climate similarity + last 21 draws pattern."""
    _setup_logging(debug)
    from datetime import date as dt_date
    from lotofacil.experimentos.data.draws_loader import load_draws
    from lotofacil.experimentos.features.padroes_similares import gerar_jogo_com_similares, salvar_jogo

    draws = load_draws()
    if not draws:
        console.print("[red]Nenhum dado histórico encontrado.[/red]")
        raise typer.Exit(1)

    target_date = data if data else dt_date.today().isoformat()
    target_concurso = concurso if concurso else draws[-1].concurso + 1

    console.print(f"[bold]Gerando jogo para concurso {target_concurso}[/bold]")
    console.print(f"Data alvo (lua+clima): {target_date}")
    console.print(f"Top-{top_n} similares | peso_similar={peso_similar} peso_padroes21={peso_padroes21}")
    console.print(f"Base: {len(draws)} concursos carregados ({draws[0].concurso}–{draws[-1].concurso})")

    result = gerar_jogo_com_similares(
        draws,
        target_date_iso=target_date,
        top_n=top_n,
        peso_similar=peso_similar,
        peso_padroes21=peso_padroes21,
        target_concurso=target_concurso,
    )

    # Print result
    from rich.table import Table as RTable
    t = RTable(title=f"Jogo Similar — Concurso {target_concurso}", box=box.SIMPLE_HEAVY)
    t.add_column("Números", style="cyan")
    t.add_column("Soma", justify="right")
    t.add_column("Pares", justify="right")
    t.add_column("Moldura", justify="right")
    t.add_column("Primos", justify="right")
    t.add_column("Fib.", justify="right")
    t.add_column("Consec.", justify="right")
    t.add_row(
        " ".join(f"{d:02d}" for d in result["dezenas"]),
        str(result["soma"]),
        str(result["pares"]),
        str(result["moldura"]),
        str(result["primos"]),
        str(result["fibonacci"]),
        "sim" if result["consecutivo"] else "não",
    )
    console.print(t)

    # Top similares table
    if result["top_similares"]:
        st = RTable(title="Top Concursos Similares", box=box.SIMPLE)
        st.add_column("Rank")
        st.add_column("Concurso")
        st.add_column("Data")
        st.add_column("Similaridade", justify="right")
        for r in result["top_similares"]:
            st.add_row(str(r["rank"]), str(r["concurso"]), r["data"], f"{r['similaridade']:.4f}")
        console.print(st)

    # Moon & climate
    console.print(f"\n🌙 Lua: phase={result['lua_hoje']['phase']:.3f}, illumination={result['lua_hoje']['illumination']:.3f}")
    c = result["clima_hoje"]
    console.print(f"☀️  Clima: {c.get('temp_sorteio', 0)*40:.1f}°C, precip={c.get('precip_sorteio', 0)*100:.0f}%")

    path = salvar_jogo(result)
    console.print(f"[green]Jogo salvo:[/green] {path}")


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
