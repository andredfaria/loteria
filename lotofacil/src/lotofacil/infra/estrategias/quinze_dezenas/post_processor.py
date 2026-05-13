"""Statistical post-processor with Simulated Annealing for 15-number predictions.

Optimizes 15-number combinations using SA to maximize combined score:
  neural probability + statistical filter compliance

Filter hierarchy:
  Level 1 (84%): Sum 171-220
  Level 2 (70%): 8-10 repeats from previous draw
  Level 2 (56%): 7-8 odd / 7-8 even
  Level 3 (55%): 9-10 frame numbers
  Level 3 (70%): 4-7 prime numbers
  Level 3 (65%): 3-5 Fibonacci numbers
  Level 3 (80%): >=2 consecutive pairs
"""

from __future__ import annotations

import math
import random
from typing import List

import numpy as np

# ── Constants ─────────────────────────────────────────────────────────────────
MOLDURA = {1, 2, 3, 4, 5, 6, 10, 11, 15, 16, 20, 21, 22, 23, 24, 25}
PRIMOS = {2, 3, 5, 7, 11, 13, 17, 19, 23}
FIBONACCI = {1, 2, 3, 5, 8, 13, 21}

FILTERS = {
    "soma": {"min": 171, "max": 220, "weight": 10.0},
    "repetidos": {"min": 8, "max": 10, "weight": 8.0},
    "pares": {"min": 7, "max": 8, "weight": 5.0},
    "moldura": {"min": 9, "max": 10, "weight": 5.0},
    "primos": {"min": 4, "max": 7, "weight": 3.0},
    "fibonacci": {"min": 3, "max": 5, "weight": 3.0},
    "consecutivos": {"min": 2, "max": 6, "weight": 3.0},
}

TARGET_COUNT = 15

# ── Scoring functions ─────────────────────────────────────────────────────────

def _soma_score(numeros: set[int]) -> float:
    s = sum(numeros)
    lo, hi = FILTERS["soma"]["min"], FILTERS["soma"]["max"]
    if lo <= s <= hi:
        return FILTERS["soma"]["weight"]
    dist = min(abs(s - lo), abs(s - hi))
    return max(-FILTERS["soma"]["weight"], -FILTERS["soma"]["weight"] * dist / 20.0)


def _repetidos_score(numeros: set[int], last_draw: list[int]) -> float:
    reps = len(numeros & set(last_draw))
    lo, hi = FILTERS["repetidos"]["min"], FILTERS["repetidos"]["max"]
    if lo <= reps <= hi:
        return FILTERS["repetidos"]["weight"]
    dist = min(abs(reps - lo), abs(reps - hi))
    return max(-FILTERS["repetidos"]["weight"], -FILTERS["repetidos"]["weight"] * dist / 3.0)


def _pares_score(numeros: set[int]) -> float:
    pares = sum(1 for n in numeros if n % 2 == 0)
    lo, hi = FILTERS["pares"]["min"], FILTERS["pares"]["max"]
    if lo <= pares <= hi:
        return FILTERS["pares"]["weight"]
    if 6 <= pares <= 9:
        return FILTERS["pares"]["weight"] * 0.5
    return -FILTERS["pares"]["weight"] * 0.5


def _moldura_score(numeros: set[int]) -> float:
    mold = sum(1 for n in numeros if n in MOLDURA)
    lo, hi = FILTERS["moldura"]["min"], FILTERS["moldura"]["max"]
    if lo <= mold <= hi:
        return FILTERS["moldura"]["weight"]
    if 8 <= mold <= 11:
        return FILTERS["moldura"]["weight"] * 0.5
    return -FILTERS["moldura"]["weight"] * 0.5


def _primos_score(numeros: set[int]) -> float:
    prim = sum(1 for n in numeros if n in PRIMOS)
    lo, hi = FILTERS["primos"]["min"], FILTERS["primos"]["max"]
    if lo <= prim <= hi:
        return FILTERS["primos"]["weight"]
    return -FILTERS["primos"]["weight"] * 0.3


def _fibonacci_score(numeros: set[int]) -> float:
    fib = sum(1 for n in numeros if n in FIBONACCI)
    lo, hi = FILTERS["fibonacci"]["min"], FILTERS["fibonacci"]["max"]
    if lo <= fib <= hi:
        return FILTERS["fibonacci"]["weight"]
    return -FILTERS["fibonacci"]["weight"] * 0.3


def _consecutivos_score(numeros: set[int]) -> float:
    s = sorted(numeros)
    cons = sum(1 for i in range(len(s) - 1) if s[i + 1] == s[i] + 1)
    if cons >= FILTERS["consecutivos"]["min"]:
        return FILTERS["consecutivos"]["weight"]
    return -FILTERS["consecutivos"]["weight"] * 0.5


def filter_score(numeros: set[int], last_draw: list[int] | None = None) -> float:
    """Score a 15-number candidate against all statistical filters."""
    score = 0.0
    score += _soma_score(numeros)
    score += _pares_score(numeros)
    score += _moldura_score(numeros)
    score += _primos_score(numeros)
    score += _fibonacci_score(numeros)
    score += _consecutivos_score(numeros)
    if last_draw is not None:
        score += _repetidos_score(numeros, last_draw)
    return score


def neural_score(numeros: set[int], probas: np.ndarray) -> float:
    """Score based on sum of neural probabilities."""
    return sum(probas[n - 1] for n in numeros)


def combined_score(numeros: set[int], probas: np.ndarray, last_draw: list[int] | None = None,
                   neural_w: float = 0.6, filter_w: float = 0.4) -> float:
    """Combined score: neural + normalized filter score."""
    total_filter_weight = sum(f["weight"] for f in FILTERS.values())
    n_score = neural_score(numeros, probas)
    f_score = filter_score(numeros, last_draw)
    f_norm = f_score / total_filter_weight
    # Normalize neural score to [0, 1] by dividing by max possible (15 * max_proba)
    max_proba = np.max(probas)
    n_norm = n_score / (TARGET_COUNT * max_proba) if max_proba > 0 else 0
    return n_norm * neural_w + (1.0 + f_norm) * filter_w


# ── Simulated Annealing Optimizer ─────────────────────────────────────────────

def simulated_annealing(
    probas: np.ndarray,
    last_draw: list[int] | None = None,
    initial: set[int] | None = None,
    n_iterations: int = 10000,
    initial_temp: float = 5.0,
    cooling_rate: float = 0.995,
    min_temp: float = 0.01,
    rng: random.Random | None = None,
) -> list[int]:
    """
    Simulated Annealing for combinatorial optimization of 15-number selection.

    State: set of 15 numbers from 1-25
    Neighbor: swap one number in the set with one outside
    Objective: maximize combined_score(neural + filters)
    """
    if rng is None:
        rng = random.Random(42)

    all_numbers = set(range(1, 26))

    # Initial state: top-15 by probability or provided
    if initial is None:
        initial = set(np.argsort(probas)[::-1][:TARGET_COUNT] + 1)

    current = set(initial)
    current_score = combined_score(current, probas, last_draw)

    best = set(current)
    best_score = current_score

    temperature = initial_temp

    for iteration in range(n_iterations):
        if temperature < min_temp:
            break

        # Generate neighbor: swap one in with one out
        current_list = sorted(current)
        outside = sorted(all_numbers - current)

        remove_num = rng.choice(current_list)
        add_num = rng.choice(outside)

        neighbor = current.copy()
        neighbor.remove(remove_num)
        neighbor.add(add_num)

        neighbor_score = combined_score(neighbor, probas, last_draw)
        delta = neighbor_score - current_score

        # Accept or reject
        if delta > 0:
            current = neighbor
            current_score = neighbor_score
            if current_score > best_score:
                best = set(current)
                best_score = current_score
        else:
            # Metropolis criterion
            acceptance_prob = math.exp(delta / temperature)
            if rng.random() < acceptance_prob:
                current = neighbor
                current_score = neighbor_score

        temperature *= cooling_rate

    return sorted(best)


def sa_with_restarts(
    probas: np.ndarray,
    last_draw: list[int] | None = None,
    n_restarts: int = 5,
    iterations_per_restart: int = 5000,
) -> list[int]:
    """Run SA multiple times with different starting points, return best result."""
    rng = random.Random(42)
    best_overall = None
    best_score_overall = -float("inf")

    for restart in range(n_restarts):
        # Different starting points
        if restart == 0:
            initial = None  # Top-15 by probability
        else:
            # Perturbed start: top-15 with some random swaps
            base = set(np.argsort(probas)[::-1][:TARGET_COUNT] + 1)
            n_swaps = restart * 2
            for _ in range(n_swaps):
                remove = rng.choice(sorted(base))
                base.remove(remove)
                available = [n for n in range(1, 26) if n not in base]
                base.add(rng.choice(available))
            initial = base

        result = simulated_annealing(
            probas, last_draw, initial,
            n_iterations=iterations_per_restart,
            initial_temp=3.0 + restart * 0.5,
            cooling_rate=0.997,
            rng=random.Random(42 + restart),
        )
        result_set = set(result)
        score = combined_score(result_set, probas, last_draw)

        if score > best_score_overall:
            best_score_overall = score
            best_overall = result

    return best_overall


# ── Legacy: candidate generation for comparison ───────────────────────────────

def optimize(
    probas: np.ndarray,
    last_draw: list[int] | None = None,
    n_candidates: int = 50000,
) -> list[int]:
    """Find the best 15 numbers using Simulated Annealing optimization."""
    return sa_with_restarts(
        probas, last_draw,
        n_restarts=5,
        iterations_per_restart=8000,
    )
