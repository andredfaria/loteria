#!/usr/bin/env python3
"""Predict Lotofácil portfolio for a target concurso.

Usage:
    python predict_portfolio.py --concurso 3675 --jogos 8
"""
from __future__ import annotations

import argparse
import itertools
import json
import sys
from pathlib import Path
from typing import List, Tuple

import numpy as np
import requests

# ── Path setup ─────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
SRC_DIR = SCRIPT_DIR / "src"
DADOS_DIR = SCRIPT_DIR / "dados"
sys.path.insert(0, str(SRC_DIR))

# ── Constants ──────────────────────────────────────────────────────────────────
COST_PER_GAME = 3.50
API_BASE = "https://loteriascaixa-api.herokuapp.com/api/lotofacil"
API_TIMEOUT = 15

_PRIMOS = {2, 3, 5, 7, 11, 13, 17, 19, 23}
_FIBONACCI = {1, 2, 3, 5, 8, 13, 21}
_MOLDURA = {1, 2, 3, 4, 5, 21, 22, 23, 24, 25}

# ── Game distribution across tiers ────────────────────────────────────────────

_DIST_TABLE = {
    1: (1, 0, 0), 2: (1, 1, 0), 3: (1, 1, 1),
    4: (2, 1, 1), 5: (2, 2, 1), 6: (2, 2, 2),
    7: (3, 2, 2), 8: (3, 3, 2), 9: (3, 3, 3),
    10: (4, 3, 3),
}


def distribute_games(n: int) -> Tuple[int, int, int]:
    """Return (conservador, equilibrado, agressivo) game counts summing to n."""
    if n in _DIST_TABLE:
        return _DIST_TABLE[n]
    # For n > 10: ~40% conserv, ~35% equil, ~25% agress
    a = max(1, n // 4)
    c = max(1, round(n * 0.4))
    e = n - c - a
    if e < 0:
        e = 0
        c = n - a
    return (c, e, a)


# ── Statistical filters ────────────────────────────────────────────────────────

def game_quality_score(game: List[int], last_draw: List[int]) -> float:
    """Return quality score in [0, 1] based on 7 statistical filters."""
    passed = 0

    # 1. Par/ímpar ratio (most common: 7-8, 8-7, 6-9, 9-6)
    pares = sum(1 for n in game if n % 2 == 0)
    if (pares, 15 - pares) in {(7, 8), (8, 7), (6, 9), (9, 6)}:
        passed += 1

    # 2. Sum in 171-220 (covers ~84% of historical draws)
    soma = sum(game)
    if 171 <= soma <= 220:
        passed += 1

    # 3. Moldura count in 8-11
    moldura = sum(1 for n in game if n in _MOLDURA)
    if 8 <= moldura <= 11:
        passed += 1

    # 4. Prime count in 4-7
    primos = sum(1 for n in game if n in _PRIMOS)
    if 4 <= primos <= 7:
        passed += 1

    # 5. Fibonacci count in 3-5
    fib = sum(1 for n in game if n in _FIBONACCI)
    if 3 <= fib <= 5:
        passed += 1

    # 6. At least one pair of consecutive numbers
    s = sorted(game)
    has_consec = any(s[i + 1] == s[i] + 1 for i in range(len(s) - 1))
    if has_consec:
        passed += 1

    # 7. Repetitions from last draw in 8-10
    repetidos = sum(1 for n in game if n in set(last_draw))
    if 8 <= repetidos <= 10:
        passed += 1

    return passed / 7


# ── Data update ────────────────────────────────────────────────────────────────

def fetch_missing_draws(dados_dir: Path, target_concurso: int) -> None:
    """Fetch concursos from (max_local+1) up to target_concurso-1 and save to dados_dir."""
    existing = {
        int(f.stem.split("_")[1])
        for f in dados_dir.glob("concurso_*.json")
        if f.stem.split("_")[1].isdigit()
    }
    max_local = max(existing, default=0)
    needed = list(range(max_local + 1, target_concurso))
    if not needed:
        print(f"  Dados já atualizados até concurso {max_local}")
        return
    print(f"  Buscando concursos {max_local + 1} → {target_concurso - 1}...")
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
            print(f"    ✓ Concurso {n} ({raw.get('data', '?')}): {raw.get('dezenas', [])}")
        except Exception as exc:
            print(f"    ✗ Concurso {n}: {exc}")


# ── Draw loader ────────────────────────────────────────────────────────────────

def load_draws_from_files(dados_dir: Path, max_concurso: int):
    """Load all Draw objects from dados_dir where concurso < max_concurso, sorted ascending."""
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


# ── Probability engine ─────────────────────────────────────────────────────────

def get_probabilities(draws) -> np.ndarray:
    """Return probability array of shape (25,) summing to 1.

    Tries ElevenNumbersStrategy ensemble (statistical + ML).
    Falls back to pure statistical, then raw frequency, on failure.
    """
    from strategies.eleven_numbers.predictor import ElevenNumbersStrategy

    strategy = ElevenNumbersStrategy()
    try:
        pred = strategy.predict(draws, approach="all")
        probas = np.array(pred.probabilidades, dtype=np.float64)
        print("  Ensemble: estatístico + ML ✓")
    except Exception as e_all:
        print(f"  Ensemble completo falhou ({e_all}), tentando apenas estatístico...")
        try:
            pred = strategy.predict(draws, approach="statistical")
            probas = np.array(pred.probabilidades, dtype=np.float64)
            print("  Estatístico ✓")
        except Exception as e_stat:
            print(f"  Estatístico também falhou ({e_stat}), usando frequência simples...")
            counts = np.zeros(25, dtype=np.float64)
            for draw in draws[-100:]:
                for n in draw.dezenas:
                    counts[n - 1] += 1
            probas = counts / counts.sum() if counts.sum() > 0 else np.ones(25) / 25

    if probas.sum() > 0:
        probas = probas / probas.sum()
    else:
        probas = np.ones(25, dtype=np.float64) / 25

    return probas


# ── Game generation ────────────────────────────────────────────────────────────

def generate_games_for_tier(
    core: List[int],
    fill_pool: List[int],
    n_games: int,
    last_draw: List[int],
) -> List[List[int]]:
    """Generate n_games games each containing all 11 core numbers + 4 from fill_pool.

    Selects the n_games combos with highest game_quality_score, deduplicating fills.
    """
    if n_games == 0:
        return []

    core_set = set(core)
    effective_pool = [n for n in fill_pool if n not in core_set]
    if len(effective_pool) < 4:
        extras = [n for n in range(1, 26) if n not in core_set and n not in effective_pool]
        effective_pool = effective_pool + extras
    effective_pool = effective_pool[:20]  # cap to avoid combinatorial explosion

    candidates: List[Tuple[float, List[int]]] = []
    seen: set = set()
    for fill in itertools.combinations(effective_pool, 4):
        game = sorted(list(core) + list(fill))
        key = tuple(game)
        if key in seen:
            continue
        seen.add(key)
        score = game_quality_score(game, last_draw)
        candidates.append((score, game))

    candidates.sort(key=lambda x: (-x[0], x[1]))

    # Pick top n_games ensuring fill diversity (no two games share all 4 fills)
    chosen: List[List[int]] = []
    used_fills: List[frozenset] = []
    for score, game in candidates:
        fills = frozenset(n for n in game if n not in core_set)
        if all(len(fills & prev) < 4 for prev in used_fills):
            chosen.append(game)
            used_fills.append(fills)
        if len(chosen) == n_games:
            break

    # Fallback: allow shared fills if not enough diverse games
    if len(chosen) < n_games:
        for score, game in candidates:
            if game not in chosen:
                chosen.append(game)
            if len(chosen) == n_games:
                break

    return chosen[:n_games]


def build_portfolio(
    core: List[int],
    ranked: List[int],
    n_games: int,
    last_draw: List[int],
) -> dict:
    """Build tiered portfolio.

    Fill pools by tier (numbers ranked after core 11):
      conservador : ranks 12-17  (6 candidates)
      equilibrado : ranks 12-22  (11 candidates)
      agressivo   : ranks 12-25  (14 candidates)
    """
    n_c, n_e, n_a = distribute_games(n_games)

    fill_conserv = ranked[11:17]
    fill_equil   = ranked[11:22]
    fill_agress  = ranked[11:25]

    return {
        "conservador": generate_games_for_tier(core, fill_conserv, n_c, last_draw),
        "equilibrado": generate_games_for_tier(core, fill_equil,   n_e, last_draw),
        "agressivo":   generate_games_for_tier(core, fill_agress,  n_a, last_draw),
    }


# ── Display ────────────────────────────────────────────────────────────────────

def print_portfolio(
    portfolio: dict,
    n_jogos: int,
    target_concurso: int,
    last_draw: List[int] | None = None,
) -> None:
    """Print the portfolio with tier headers, quality bars and cost summary."""
    if last_draw is None:
        last_draw = list(range(1, 16))

    tier_meta = {
        "conservador": ("CONSERVADOR", "Fills: top-6 após o core — menor variação"),
        "equilibrado": ("EQUILIBRADO", "Fills: top-11 após o core — variação moderada"),
        "agressivo":   ("AGRESSIVO",   "Fills: todos após o core — máxima diversidade"),
    }

    total_games = sum(len(v) for v in portfolio.values())
    total_cost = total_games * COST_PER_GAME

    print(f"\n{'═'*58}")
    print(f"  PORTFÓLIO LOTOFÁCIL — Concurso {target_concurso}")
    print(f"  {total_games} jogos · R${total_cost:.2f}")
    print(f"{'═'*58}")

    game_idx = 1
    for tier_key in ("conservador", "equilibrado", "agressivo"):
        games = portfolio.get(tier_key, [])
        if not games:
            continue
        label, desc = tier_meta[tier_key]
        plural = "s" if len(games) > 1 else ""
        print(f"\n  ── {label} ({len(games)} jogo{plural}) ──")
        print(f"     {desc}")
        for game in games:
            score = game_quality_score(game, last_draw)
            filters_ok = round(score * 7)
            bar = "█" * filters_ok + "░" * (7 - filters_ok)
            nums = "  ".join(f"{n:02d}" for n in sorted(game))
            soma = sum(game)
            pares = sum(1 for n in game if n % 2 == 0)
            print(f"\n  Jogo {game_idx:02d}: {nums}")
            print(f"          Qualidade [{bar}] {filters_ok}/7  |  Soma {soma}  |  {pares}P/{15-pares}I  |  R${COST_PER_GAME:.2f}")
            game_idx += 1

    # Summary
    expected_roi = total_games * (
        (1 / 10)    * 7.00 +
        (1 / 55)    * 14.00 +
        (1 / 691)   * 35.00 +
        (1 / 21791) * 2_000.00
    )
    print(f"\n{'─'*58}")
    print(f"  Total: {total_games} jogos · Custo: R${total_cost:.2f}")
    print(f"  Retorno esperado: R${expected_roi:.2f}"
          f"  (ROI: {(expected_roi - total_cost) / total_cost * 100:.1f}%)")
    print(f"{'═'*58}\n")


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Gera portfólio de apostas Lotofácil para o concurso alvo."
    )
    parser.add_argument("--concurso", type=int, required=True,
                        help="Concurso alvo (ex: 3675)")
    parser.add_argument("--jogos", type=int, default=8,
                        help="Quantidade de jogos no portfólio (padrão: 8)")
    args = parser.parse_args()

    print(f"\n{'═'*58}")
    print(f"  PORTFÓLIO LOTOFÁCIL — Concurso {args.concurso}")
    print(f"{'═'*58}")

    print("\n[1/4] Atualizando dados via API...")
    fetch_missing_draws(DADOS_DIR, args.concurso)

    print("\n[2/4] Carregando histórico de sorteios...")
    draws = load_draws_from_files(DADOS_DIR, args.concurso)
    if not draws:
        print("  ERRO: nenhum concurso carregado. Verifique a pasta dados/.")
        sys.exit(1)
    print(f"  {len(draws)} concursos carregados  "
          f"(concurso {draws[0].concurso} → {draws[-1].concurso})")

    last_draw = draws[-1].dezenas

    print("\n[3/4] Calculando probabilidades (ensemble estatístico + ML)...")
    probas = get_probabilities(draws)

    ranked = [int(x) for x in np.argsort(probas)[::-1] + 1]  # numbers best → worst
    core = ranked[:11]
    print(f"  Core 11 números: {sorted(core)}")
    print(f"  Probabilidade média core: {np.mean([probas[n-1] for n in core]):.4f}")

    print("\n[4/4] Gerando portfólio...")
    portfolio = build_portfolio(core, ranked, args.jogos, last_draw)

    print_portfolio(portfolio, args.jogos, args.concurso, last_draw)


if __name__ == "__main__":
    main()
