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
from rich.panel import Panel
from rich import box

# Ensure src/ is in sys.path before any local imports
_SRC = Path(__file__).resolve().parent.parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


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
    from lotofacil.experimentos.data.lunar_loader import get_lunar_features_dict
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
    force: bool = typer.Option(
        False, "--force",
        help="Recompute and overwrite existing cache files (repairs stale/wrong data).",
    ),
    debug: bool = typer.Option(False, "--debug"),
) -> None:
    """Backfill lunar cache for all/selected historical draws.

    Without --force, only missing dates are computed. With --force, every
    selected date is recomputed and its cache file overwritten — use this to
    repair caches written by an older, buggy version of the phase calculation.
    """
    _setup_logging(debug)
    from lotofacil.experimentos.data.draws_loader import load_draws
    from lotofacil.experimentos.data.lunar_loader import (
        compute_lunar_features, recompute_lunar_cache, _parse_iso,
    )

    draws = load_draws()
    if ultimos:
        draws = draws[-ultimos:]
    if from_c:
        draws = [d for d in draws if d.concurso >= from_c]
    if to_c:
        draws = [d for d in draws if d.concurso <= to_c]

    computed = 0
    errors = 0
    label = "Recomputing" if force else "Backfilling"
    with console.status(f"[bold green]{label} lunar data..."):
        for draw in draws:
            iso = _parse_iso(draw.data)
            if not iso:
                errors += 1
                continue
            arr = recompute_lunar_cache(iso) if force else compute_lunar_features(iso)
            if arr.sum() == 0 and not any(e in iso for e in ["1900", "error"]):
                errors += 1
            computed += 1

    verb = "recomputed" if force else "cached"
    console.print(f"[green]Done:[/green] {computed} dates {verb}, {errors} errors.")


# ── train ──────────────────────────────────────────────────────────────────────

@app.command("train")
def train(
    config_sig: str = typer.Option("base+temp+priors", "--config",
                                    help="Feature config signature. e.g. 'base+temp+priors+clima+lua'"),
    epochs: int = typer.Option(None, "--epochs", help="Override max epochs."),
    n_draws: int = typer.Option(None, "--n-draws", help="Use only last N draws."),
    seed: int = typer.Option(None, "--seed", help="Override RANDOM_SEED for reproducibility."),
    window_size: int = typer.Option(None, "--window-size", help="Override LSTM window (past draws as context)."),
    name: str = typer.Option(None, "--name", help="Custom model stem for versioning (e.g. 'abc1_meu_treino')."),
    fast: bool = typer.Option(False, "--fast", help="Use smaller LSTM model for faster CPU training."),
    debug: bool = typer.Option(False, "--debug"),
) -> None:
    """Train a NeuralModular model for the given feature config and save it."""
    _setup_logging(debug)
    try:
        import tensorflow  # noqa: F401
    except ImportError:
        console.print("[red]Erro:[/red] TensorFlow não encontrado neste ambiente.")
        console.print("Reconstrua a imagem Docker: [bold]docker-compose build --no-cache[/bold]")
        raise typer.Exit(1)
    import dataclasses
    import lotofacil.experimentos.config as lab_cfg
    from lotofacil.experimentos.config import MODELS_DIR
    from lotofacil.experimentos.data.feature_flags import FeatureConfig
    from lotofacil.experimentos.data.draws_loader import load_draws, load_draws_last_n
    from lotofacil.experimentos.models.neural_modular import NeuralModular

    cfg = FeatureConfig.from_signature(config_sig)
    if window_size:
        cfg = dataclasses.replace(cfg, window_size=window_size)
    console.print(f"Config: [cyan]{cfg.signature()}[/cyan]")

    draws = load_draws_last_n(n_draws) if n_draws else load_draws()
    if draws:
        console.print(f"Draws: {len(draws)} ({draws[0].concurso}–{draws[-1].concurso})")
    else:
        console.print("Draws: 0 (no data loaded)")

    if epochs:
        lab_cfg.LSTM_EPOCHS = epochs
    if seed:
        lab_cfg.RANDOM_SEED = seed

    if fast:
        console.print("[yellow]Modo rápido:[/yellow] modelo menor (LSTM 64/32/16) para treino mais rápido.")
    model = NeuralModular(cfg, fast=fast)
    console.print("Training... (this may take a while)")
    model.fit(draws)

    save_path = MODELS_DIR / f"neural_{name}.keras" if name else None
    model.save(save_path)
    stem = name if name else f"{cfg.signature()}"
    console.print(f"[green]Saved:[/green] neural_{stem}.keras")
    # Emitted for dashboard registry to capture the saved path.
    # Plain print() (not console.print) so Rich não quebra o caminho em
    # múltiplas linhas quando rodando em subprocess sem tty (largura 80).
    actual_path = save_path or (MODELS_DIR / f"neural_{cfg.signature()}.keras")
    print(f"TREINO_MODELO_PATH: {actual_path}", flush=True)


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


# ── analisar ───────────────────────────────────────────────────────────────────

@app.command("analisar")
def analisar(
    top_n: int = typer.Option(20, "--top-n", help="Top resultados por categoria."),
    windows_str: str = typer.Option("10,30,50,100", "--windows",
                                    help="Janelas de frequência (separadas por vírgula)."),
    target: str = typer.Option("both", "--target",
                                help="Tamanho do jogo: 11, 15, both"),
    save: bool = typer.Option(True, "--save/--no-save",
                               help="Salvar relatório JSON em saida/analises/"),
    debug: bool = typer.Option(False, "--debug"),
) -> None:
    """Análise completa: frequência, co-ocorrência, importância RF e jogos históricos."""
    _setup_logging(debug)

    from datetime import datetime
    from lotofacil.experimentos.config import ANALYSIS_DIR
    from lotofacil.experimentos.data.draws_loader import load_draws
    from lotofacil.experimentos.analysis.analisador import AnalisadorCompleto, salvar_relatorio

    windows = tuple(int(w.strip()) for w in windows_str.split(",") if w.strip())

    targets_map = {"11": (11,), "15": (15,), "both": (11, 15)}
    targets = targets_map.get(target, (11, 15))

    draws = load_draws()
    if not draws:
        console.print("[red]Nenhum dado encontrado. Execute: lotofacil dados atualizar --all[/red]")
        raise typer.Exit(1)

    console.print(f"[bold]Carregados {len(draws)} concursos ({draws[0].concurso}–{draws[-1].concurso})[/bold]")
    console.print(f"Janelas: {windows} | Target: {target} | Top-N: {top_n}")
    console.print()

    with console.status("[bold green]Rodando análise completa...") as status:
        analisador = AnalisadorCompleto(draws)
        resultado = analisador.analisar(top_n=top_n, windows=windows, targets=targets)

    _exibir_resultado(console, resultado, top_n)

    if save:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = ANALYSIS_DIR / f"analise_completa_{timestamp}.json"
        salvar_relatorio(resultado, out_path)
        console.print(f"\n[green]Relatório salvo:[/green] {out_path}")


def _exibir_resultado(console, resultado: dict, top_n: int) -> None:
    from rich.table import Table
    from rich import box

    meta = resultado["metadata"]

    painel_texto = (
        f"Total de concursos: [cyan]{meta['total_draws']}[/cyan]\n"
        f"Range: [cyan]{meta['concurso_range'][0]}[/cyan] → [cyan]{meta['concurso_range'][1]}[/cyan]\n"
        f"Período: [cyan]{meta['data_range'][0]}[/cyan] → [cyan]{meta['data_range'][1]}[/cyan]"
    )
    console.print(Panel(painel_texto, title="📊  Análise Completa — Lotofácil",
                        box=box.DOUBLE_EDGE))
    console.print()

    if "frequencia" in resultado:
        freq = resultado["frequencia"]
        ranking = freq["ranking"]
        ranking.sort(key=lambda r: r.get("total", 0), reverse=True)

        table = Table(title="Frequência por Número", box=box.SIMPLE_HEAVY)
        table.add_column("Nº", justify="right", style="cyan")
        cols = [c for c in ["ultimos_10", "ultimos_30", "ultimos_50", "ultimos_100", "total"]
                if c in ranking[0]]
        labels_map = {
            "ultimos_10": "Últ.10", "ultimos_30": "Últ.30",
            "ultimos_50": "Últ.50", "ultimos_100": "Últ.100", "total": "Total",
        }
        for c in cols:
            table.add_column(labels_map.get(c, c), justify="right")
        for row in ranking[:15]:
            vals = [str(row["numero"])] + [str(row[c]) for c in cols]
            table.add_row(*vals)
        console.print(table)
        console.print()

    if "coocorrencia" in resultado:
        cooc = resultado["coocorrencia"]
        for nome in ("pares", "triplas", "quadruplas", "quintuplas"):
            if nome not in cooc:
                continue
            data = cooc[nome]
            table = Table(
                title=f"Top {min(top_n, 10)} {nome.capitalize()} mais frequentes "
                      f"({data['total_combos_unicas']} combos únicas)",
                box=box.SIMPLE_HEAVY,
            )
            table.add_column("Sequência", style="cyan")
            table.add_column("Freq.", justify="right")
            table.add_column("%", justify="right")
            for entry in data["top"][:10]:
                seq = " ".join(f"{n:02d}" for n in entry["sequencia"])
                table.add_row(seq, str(entry["frequencia"]), f"{entry['proporcao']:.1f}%")
            console.print(table)
            console.print()

    if "importancia_ml" in resultado:
        imp = resultado["importancia_ml"]
        table = Table(
            title=f"Top {min(top_n, 15)} Features mais importantes (Random Forest)",
            box=box.SIMPLE_HEAVY,
        )
        table.add_column("Feature", style="cyan")
        table.add_column("Importância Média", justify="right")
        table.add_column("Desvio Padrão", justify="right")
        for entry in imp["top_features_globais"][:15]:
            table.add_row(
                entry["feature"],
                f"{entry['importancia_media']:.6f}",
                f"{entry['importancia_std']:.6f}",
            )
        console.print(table)
        console.print()

    for target in (11, 15):
        key = f"jogos_{target}_dezenas"
        if key not in resultado:
            continue
        jdata = resultado[key]
        console.print(
            Panel(
                f"[bold]Análise de jogos de {target} dezenas[/bold]",
                box=box.SIMPLE,
            )
        )

        for origem, label in [("top_por_frequencia", "Frequência"),
                              ("top_por_ml", "Random Forest")]:
            if origem not in jdata or not jdata[origem]:
                continue
            table = Table(
                title=f"Top jogos ({label})",
                box=box.SIMPLE_HEAVY,
            )
            table.add_column("Jogo", style="cyan")
            table.add_column("Soma", justify="right")
            table.add_column("Média", justify="right")
            table.add_column(">=11", justify="right")
            table.add_column(">=12", justify="right")
            table.add_column(">=13", justify="right")
            table.add_column(">=14", justify="right")
            table.add_column(">=15", justify="right")
            for jogo_data in jdata[origem]:
                jogo_str = " ".join(f"{n:02d}" for n in jogo_data["jogo"])
                dist = jogo_data["distribuicao"]
                table.add_row(
                    jogo_str,
                    str(jogo_data["soma"]),
                    f"{jogo_data['media_acertos']:.1f}",
                    str(dist.get("acertos_11", 0)),
                    str(dist.get("acertos_12", 0)),
                    str(dist.get("acertos_13", 0)),
                    str(dist.get("acertos_14", 0)),
                    str(dist.get("acertos_15", 0)),
                )
            console.print(table)
            console.print()


# ── gerar-melhor-jogo ──────────────────────────────────────────────────────────

@app.command("gerar-melhor-jogo")
def gerar_melhor_jogo(
    concurso: int = typer.Option(0, "--concurso", "-c", help="Concurso alvo (0 = auto)."),
    save: bool = typer.Option(True, "--save/--no-save", help="Salvar em saida/jogos/"),
    debug: bool = typer.Option(False, "--debug"),
) -> None:
    """Gera o melhor jogo de 15 dezenas usando ensemble multi-sinal + SA."""
    _setup_logging(debug)
    from datetime import date as dt_date
    from lotofacil.experimentos.config import PROJECT_ROOT
    from lotofacil.experimentos.data.draws_loader import load_draws
    from lotofacil.experimentos.analysis.gerador_melhor_jogo import gerar_melhor_jogo as gerar, salvar_resultado

    draws = load_draws()
    if not draws:
        console.print("[red]Sem dados.[/red]")
        raise typer.Exit(1)

    target_concurso = concurso if concurso else draws[-1].concurso + 1
    target_date = dt_date.today().isoformat()

    console.print(f"[bold]Gerando melhor jogo para concurso {target_concurso} ({target_date})[/bold]")
    console.print(f"Base: {len(draws)} concursos ({draws[0].concurso}–{draws[-1].concurso})")
    console.print()

    with console.status("[bold green]Otimizando jogo com ensemble multi-sinal + SA..."):
        resultado = gerar(draws, target_concurso, target_date)

    _exibir_melhor_jogo(console, resultado)

    if save:
        saida_dir = PROJECT_ROOT / "saida" / "jogos"
        saida_dir.mkdir(parents=True, exist_ok=True)
        out_path = saida_dir / f"melhor_jogo_{target_concurso}.json"
        salvar_resultado(resultado, out_path)
        console.print(f"\n[green]Jogo salvo:[/green] {out_path}")

    jogos_dir = PROJECT_ROOT / "saida" / "jogos"
    console.print(f"\n[bold]💾 Arquivos em:[/bold] {jogos_dir}")


def _exibir_melhor_jogo(console, r: dict) -> None:
    from rich.table import Table
    from rich.panel import Panel
    from rich import box

    jogo = r["jogo"]
    est = r["estatisticas"]
    av = r["avaliacao_historica"]
    dist = av["distribuicao"]

    jogo_str = "  ".join(f"{n:02d}" for n in jogo)
    console.print(Panel(
        f"[bold cyan]🎯 Jogo para Concurso {r['metadata']['target_concurso']}[/bold cyan]\n\n"
        f"[yellow]{jogo_str}[/yellow]\n\n"
        f"Soma: {est['soma']} | Pares: {est['pares']}/{est['impares']} | "
        f"Moldura: {est['moldura']} | Primos: {est['primos']} | "
        f"Fib: {est['fibonacci']} | Consec: {est['consecutivos']}\n"
        f"Filter Score: {est['filter_score']}",
        box=box.DOUBLE_EDGE,
    ))

    table = Table(title="Avaliação Histórica (3737 concursos)", box=box.SIMPLE_HEAVY)
    table.add_column("Métrica", style="cyan")
    table.add_column("Valor", justify="right")
    table.add_row("Média de acertos", str(av["media_acertos"]))
    table.add_row("≥11 acertos", f"{dist['11']}x ({av['prob_acertos_11']}%)")
    table.add_row("≥12 acertos", f"{dist['12']}x")
    table.add_row("≥13 acertos", f"{dist['13']}x")
    table.add_row("≥14 acertos", f"{dist['14']}x")
    table.add_row("15 acertos", f"{dist['15']}x ({av['prob_acertos_15']}%)")
    table.add_row("Máx acertos", str(av["max_acertos"]))
    console.print(table)

    pesos = Table(title="Pesos do Ensemble", box=box.SIMPLE)
    pesos.add_column("Sinal", style="cyan")
    pesos.add_column("Peso", justify="right")
    pesos.add_column("Score", justify="right")
    for nome, peso in r["pesos_ensemble"].items():
        score = r["score_por_sinal"].get(nome, 0)
        pesos.add_row(nome.capitalize(), f"{peso*100:.0f}%", f"{score:.4f}")
    console.print(pesos)

    if r["top_similares"]:
        sim_table = Table(title="Top Concursos Similares (Lua+Clima)", box=box.SIMPLE)
        sim_table.add_column("Rank")
        sim_table.add_column("Concurso")
        sim_table.add_column("Data")
        sim_table.add_column("Similaridade", justify="right")
        for s in r["top_similares"][:5]:
            sim_table.add_row(str(s["rank"]), str(s["concurso"]), s["data"], str(s["similaridade"]))
        console.print(sim_table)

    console.print(f"\n🌙 Lua: phase={r['lua_hoje']['phase']} illum={r['lua_hoje']['illumination']} "
                  f"{'(🌕 Cheia)' if r['lua_hoje']['is_full'] else '(🌑 Nova)' if r['lua_hoje']['is_new'] else ''}")
    console.print(f"☀️  Clima SP: {r['clima_hoje']['temp_sorteio']}°C | "
                  f"precip={r['clima_hoje']['precip_sorteio']} | "
                  f"wcode={r['clima_hoje']['wcode_sorteio']}")

    console.print(f"\n[dim]{r['explicacao']}[/dim]")


# ── validar-algoritmo ──────────────────────────────────────────────────────────

@app.command("validar-algoritmo")
def validar_algoritmo(
    start: int = typer.Option(2000, "--start", help="Primeiro concurso do backtest."),
    retrain: int = typer.Option(50, "--retrain", help="Re-treinar RF a cada N concursos."),
    save: bool = typer.Option(True, "--save/--no-save"),
    debug: bool = typer.Option(False, "--debug"),
) -> None:
    """Walk-forward backtest determinístico para validar acurácia do ensemble."""
    _setup_logging(debug)
    from datetime import datetime
    from lotofacil.experimentos.config import PROJECT_ROOT
    from lotofacil.experimentos.data.draws_loader import load_draws
    from lotofacil.experimentos.analysis.validador_backtest import (
        rodar_backtest_walkforward, salvar_backtest, ESTRATEGIAS,
    )

    draws = load_draws()
    if not draws:
        console.print("[red]Sem dados.[/red]")
        raise typer.Exit(1)

    console.print(f"[bold]Walk-forward: concurso {start} → {draws[-1].concurso - 1}[/bold]")
    console.print(f"Estratégias: {len(ESTRATEGIAS)} | Re-treino RF: a cada {retrain} concursos")
    console.print()

    with console.status("[bold green]Rodando backtest walk-forward..."):
        resultado = rodar_backtest_walkforward(draws, start_concurso=start, retrain_every=retrain)

    _exibir_validacao(console, resultado)

    if save:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = PROJECT_ROOT / "saida" / "analises" / f"validacao_algoritmo_{ts}.json"
        salvar_backtest(resultado, out_path)
        console.print(f"\n[green]Relatório salvo:[/green] {out_path}")


def _exibir_validacao(console, resultado: dict) -> None:
    # Import local: `ESTRATEGIAS` vive em analysis/validador_backtest.py e era
    # importada apenas dentro de validar_algoritmo(), outra função — esta aqui
    # estourava NameError ao montar a tabela. Mantido local para preservar o
    # padrão de import tardio do módulo (evita puxar TensorFlow no --help).
    from lotofacil.experimentos.analysis.validador_backtest import ESTRATEGIAS

    from rich.table import Table
    from rich.panel import Panel
    from rich import box

    mel = resultado.get("melhor_estrategia")

    if mel:
        console.print(Panel(
            f"[bold green]🏆 Melhor Estratégia: {mel['nome']}[/bold green]\n"
            f"Taxa ≥11: [cyan]{mel['taxa_11']}%[/cyan] | Taxa ≥13: [cyan]{mel['taxa_13']}%[/cyan]",
            box=box.DOUBLE_EDGE,
        ))
        console.print()

    table = Table(title="Comparativo de Estratégias", box=box.SIMPLE_HEAVY)
    table.add_column("Estratégia", style="cyan")
    table.add_column("N", justify="right")
    table.add_column("Média", justify="right")
    table.add_column("≥11", justify="right")
    table.add_column("≥12", justify="right")
    table.add_column("≥13", justify="right")
    table.add_column("≥14", justify="right")
    table.add_column("≥15", justify="right")
    table.add_column("a cada N", justify="right")
    table.add_column("Sequência", justify="right")

    for nome, _ in ESTRATEGIAS:
        dados = resultado["resultados"].get(nome, {})
        if "erro" in dados:
            table.add_row(nome, "ERRO", "—", "—", "—", "—", "—", "—", "—", "—")
            continue
        table.add_row(
            nome,
            str(dados["total_concursos"]),
            f"{dados['media_acertos']:.2f}",
            f"{dados['distribuicao']['11']}x ({dados['taxa_acerto_11']}%)",
            f"{dados['distribuicao']['12']}x ({dados['taxa_acerto_12']}%)",
            f"{dados['distribuicao']['13']}x ({dados['taxa_acerto_13']}%)",
            f"{dados['distribuicao']['14']}x ({dados['taxa_acerto_14']}%)",
            f"{dados['distribuicao']['15']}x ({dados['taxa_acerto_15']}%)",
            str(dados.get("concursos_para_acertar_11", "—")),
            str(dados.get("maior_sequencia_acertos", "—")),
        )

    console.print(table)
    console.print()

    for nome, _ in ESTRATEGIAS:
        dados = resultado["resultados"].get(nome, {})
        if "erro" in dados or not dados.get("hit_details"):
            continue
        hits_13 = [h for h in dados["hit_details"] if h["hits"] >= 13]
        if hits_13:
            t = Table(title=f"⭐ {nome} — Acertos ≥13", box=box.SIMPLE)
            t.add_column("Concurso")
            t.add_column("Data")
            t.add_column("Hits", justify="right")
            for h in hits_13[:10]:
                t.add_row(str(h["concurso"]), h["data"], str(h["hits"]))
            console.print(t)
            console.print()


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
