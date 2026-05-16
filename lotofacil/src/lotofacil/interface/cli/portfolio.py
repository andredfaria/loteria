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
    4: (2, 1, 1), 5: (2, 2, 1), 6: (2, 2, 2),
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
    from lotofacil.dominio.entidades import Sorteio as Draw

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
        from lotofacil.experimentos.data.feature_flags import FeatureConfig
        from lotofacil.experimentos.models.neural_modular import NeuralModular
        from lotofacil.experimentos.features.builder import ModularFeatureBuilder

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
        from lotofacil.infra.estrategias.onze_dezenas.predictor import ElevenNumbersStrategy

        pred = ElevenNumbersStrategy().predict(draws, approach="all")
        probas = np.array(pred.probabilidades, dtype=np.float64)
        if probas.sum() > 0:
            probas /= probas.sum()
        console.print("  [green]Ensemble: estatístico + ML ✓[/green]")
        return probas
    except Exception as e_all:
        console.print(f"  [yellow]Ensemble falhou ({e_all}), tentando estatístico...[/yellow]")

    try:
        from lotofacil.infra.estrategias.onze_dezenas.predictor import ElevenNumbersStrategy

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

    console.print(f"\n{'═'*58}")
    console.print(f"  [bold cyan]PORTFÓLIO LOTOFÁCIL — Concurso {target_concurso}[/bold cyan]")
    console.print(f"  {total_games} jogos · R${total_cost:.2f}")
    console.print(f"{'═'*58}")

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
                f"          Qualidade [{bar}] {filters_ok}/7"
                f"  |  Soma {soma}"
                f"  |  {pares}P/{15-pares}I"
                f"  |  R${COST_PER_GAME:.2f}"
            )
            game_idx += 1

    expected_roi = total_games * (
        (1 / 10) * 7.00 + (1 / 55) * 14.00 +
        (1 / 691) * 35.00 + (1 / 21791) * 2_000.00
    )
    console.print(f"\n{'─'*58}")
    console.print(f"  Total: {total_games} jogos · Custo: R${total_cost:.2f}")
    console.print(
        f"  Retorno esperado: R${expected_roi:.2f}"
        f"  (ROI: {(expected_roi - total_cost) / total_cost * 100:.1f}%)"
    )
    console.print(f"{'═'*58}\n")


# ── Typer commands ─────────────────────────────────────────────────────────────

_DADOS_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent / "dados"


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

    _saida = Path(__file__).resolve().parent.parent.parent / "saida" / "jogos"
    _saida.mkdir(parents=True, exist_ok=True)
    out = _saida / f"portfolio_{concurso}.json"
    out.write_text(
        json.dumps({"concurso": concurso, "jogos": portfolio}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    console.print(f"\n  [dim]💾 Salvo em saida/jogos/portfolio_{concurso}.json[/dim]")


@app.command("validar")
def portfolio_validar(
    concurso: int = typer.Argument(..., help="Concurso a validar (ex: 3675)"),
) -> None:
    """Simula e valida portfólio gerado para um concurso já realizado."""
    result_path = _DADOS_DIR / f"concurso_{concurso}.json"
    if not result_path.exists():
        console.print(f"[red]Sorteio do concurso {concurso} não encontrado em dados/.[/red]")
        console.print("Execute: lotofacil dados atualizar")
        raise typer.Exit(1)

    raw = json.loads(result_path.read_text(encoding="utf-8"))
    actual_dezenas = sorted(int(d) for d in raw["dezenas"])
    console.print(f"\nSorteio real (concurso {concurso}): "
                  + " ".join(f"{n:02d}" for n in actual_dezenas))

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
