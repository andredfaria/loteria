"""Statistical post-processor for neural predictions (optimized for 11 numbers).

Applies hierarchical filters from technical reports, recalibrated for 11-number predictions.

Recalibration rationale (15 → 11 numbers, scale factor ~0.73):
  Sum: 11 numbers from 1-25 → expected range 135-170
  Repeats: 6-8 from previous 15-number draw
  Odd/Even: 5-6 even (balanced)
  Frame: 6-8 frame numbers
  Primes: 3-5 primes
  Fibonacci: 2-4 fibonacci
  Consecutive: >=1 consecutive pair
"""

from __future__ import annotations

import random
from typing import List

import numpy as np

# ── Constants ─────────────────────────────────────────────────────────────────
MOLDURA = {1, 2, 3, 4, 5, 6, 10, 11, 15, 16, 20, 21, 22, 23, 24, 25}
PRIMOS = {2, 3, 5, 7, 11, 13, 17, 19, 23}
FIBONACCI = {1, 2, 3, 5, 8, 13, 21}

# Filter ranges RECALIBRATED for 11-number predictions
FILTERS = {
    "soma": {"min": 135, "max": 170, "weight": 10.0},
    "repetidos": {"min": 6, "max": 8, "weight": 8.0},
    "pares": {"min": 5, "max": 6, "weight": 5.0},
    "moldura": {"min": 6, "max": 8, "weight": 5.0},
    "primos": {"min": 3, "max": 5, "weight": 3.0},
    "fibonacci": {"min": 2, "max": 4, "weight": 3.0},
    "consecutivos": {"min": 1, "max": 5, "weight": 3.0},
}

N_CANDIDATES = 50000
TARGET_COUNT = 11

# ── Scoring functions ─────────────────────────────────────────────────────────

def _soma_score(numeros: list[int]) -> float:
    s = sum(numeros)
    lo, hi = FILTERS["soma"]["min"], FILTERS["soma"]["max"]
    if lo <= s <= hi:
        return FILTERS["soma"]["weight"]
    dist = min(abs(s - lo), abs(s - hi))
    return max(-FILTERS["soma"]["weight"], -FILTERS["soma"]["weight"] * dist / 15.0)


def _repetidos_score(numeros: list[int], last_draw: list[int]) -> float:
    reps = len(set(numeros) & set(last_draw))
    lo, hi = FILTERS["repetidos"]["min"], FILTERS["repetidos"]["max"]
    if lo <= reps <= hi:
        return FILTERS["repetidos"]["weight"]
    dist = min(abs(reps - lo), abs(reps - hi))
    return max(-FILTERS["repetidos"]["weight"], -FILTERS["repetidos"]["weight"] * dist / 3.0)


def _pares_score(numeros: list[int]) -> float:
    pares = sum(1 for n in numeros if n % 2 == 0)
    lo, hi = FILTERS["pares"]["min"], FILTERS["pares"]["max"]
    if lo <= pares <= hi:
        return FILTERS["pares"]["weight"]
    if 4 <= pares <= 7:
        return FILTERS["pares"]["weight"] * 0.5
    return -FILTERS["pares"]["weight"] * 0.5


def _moldura_score(numeros: list[int]) -> float:
    mold = sum(1 for n in numeros if n in MOLDURA)
    lo, hi = FILTERS["moldura"]["min"], FILTERS["moldura"]["max"]
    if lo <= mold <= hi:
        return FILTERS["moldura"]["weight"]
    if 5 <= mold <= 9:
        return FILTERS["moldura"]["weight"] * 0.5
    return -FILTERS["moldura"]["weight"] * 0.5


def _primos_score(numeros: list[int]) -> float:
    prim = sum(1 for n in numeros if n in PRIMOS)
    lo, hi = FILTERS["primos"]["min"], FILTERS["primos"]["max"]
    if lo <= prim <= hi:
        return FILTERS["primos"]["weight"]
    return -FILTERS["primos"]["weight"] * 0.3


def _fibonacci_score(numeros: list[int]) -> float:
    fib = sum(1 for n in numeros if n in FIBONACCI)
    lo, hi = FILTERS["fibonacci"]["min"], FILTERS["fibonacci"]["max"]
    if lo <= fib <= hi:
        return FILTERS["fibonacci"]["weight"]
    return -FILTERS["fibonacci"]["weight"] * 0.3


def _consecutivos_score(numeros: list[int]) -> float:
    s = sorted(numeros)
    cons = sum(1 for i in range(len(s) - 1) if s[i + 1] == s[i] + 1)
    if cons >= FILTERS["consecutivos"]["min"]:
        return FILTERS["consecutivos"]["weight"]
    return -FILTERS["consecutivos"]["weight"] * 0.5


def score_candidate(numeros: list[int], last_draw: list[int] | None = None) -> float:
    """Score a candidate combination against all statistical filters."""
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


# ── Candidate generation (smart) ──────────────────────────────────────────────

def generate_candidates(
    probas: np.ndarray,
    base_selection: list[int],
    n_candidates: int = N_CANDIDATES,
) -> list[list[int]]:
    """Generate candidates by intelligent perturbation of base selection.

    Strategy:
    - 40%: targeted swaps (replace lowest prob with highest prob outside)
    - 25%: filter-guided swaps (swap to improve specific filter)
    - 20%: probability-weighted sampling
    - 10%: light perturbation (1-2 swaps)
    - 5%: random
    """
    all_numbers = list(range(1, 26))
    candidates = []

    n_targeted = int(n_candidates * 0.40)
    n_filter_guided = int(n_candidates * 0.25)
    n_weighted = int(n_candidates * 0.20)
    n_light = int(n_candidates * 0.10)
    n_random = n_candidates - n_targeted - n_filter_guided - n_weighted - n_light

    # Targeted swaps: swap out low-prob numbers, swap in high-prob numbers
    for _ in range(n_targeted):
        cand = base_selection.copy()
        n_swaps = random.randint(1, 3)
        for _ in range(n_swaps):
            # Remove the number with lowest probability in candidate
            worst_in = min(cand, key=lambda n: probas[n - 1])
            cand.remove(worst_in)
            # Add a number with high probability not in candidate
            available = [n for n in all_numbers if n not in cand]
            weights = probas[np.array(available) - 1]
            weights = weights / weights.sum()
            new_num = np.random.choice(available, p=weights)
            cand.append(int(new_num))
        candidates.append(sorted(cand))

    # Filter-guided swaps: identify weakest filter and swap to improve it
    for _ in range(n_filter_guided):
        cand = base_selection.copy()
        # Randomly pick a filter to improve
        filter_to_fix = random.choice(list(FILTERS.keys()))
        cand = _apply_filter_swap(cand, filter_to_fix, probas, all_numbers)
        candidates.append(sorted(cand))

    # Probability-weighted sampling
    proba_normalized = probas / probas.sum()
    for _ in range(n_weighted):
        cand = sorted(np.random.choice(all_numbers, size=TARGET_COUNT, replace=False, p=proba_normalized).tolist())
        candidates.append(cand)

    # Light perturbation (1-2 swaps from base)
    for _ in range(n_light):
        cand = base_selection.copy()
        for _ in range(random.randint(1, 2)):
            idx = random.randint(0, len(cand) - 1)
            removed = cand.pop(idx)
            available = [n for n in all_numbers if n not in cand]
            new_num = random.choice(available)
            cand.append(new_num)
        candidates.append(sorted(cand))

    # Pure random
    for _ in range(n_random):
        cand = sorted(random.sample(all_numbers, TARGET_COUNT))
        candidates.append(cand)

    return candidates


def _apply_filter_swap(cand: list[int], filter_name: str, probas: np.ndarray, all_numbers: list[int]) -> list[int]:
    """Make a swap to try to improve a specific filter."""
    if filter_name == "soma":
        s = sum(cand)
        if s > FILTERS["soma"]["max"]:
            # Remove highest, add lowest available
            worst = max(cand)
            cand.remove(worst)
            available = sorted([n for n in all_numbers if n not in cand])
            cand.append(available[0])
        elif s < FILTERS["soma"]["min"]:
            worst = min(cand)
            cand.remove(worst)
            available = sorted([n for n in all_numbers if n not in cand], reverse=True)
            cand.append(available[0])

    elif filter_name == "pares":
        pares = sum(1 for n in cand if n % 2 == 0)
        if pares < FILTERS["pares"]["min"]:
            # Swap odd for even
            odds = [n for n in cand if n % 2 != 0]
            if odds:
                cand.remove(random.choice(odds))
                evens = [n for n in all_numbers if n not in cand and n % 2 == 0]
                if evens:
                    cand.append(random.choice(evens))
        elif pares > FILTERS["pares"]["max"]:
            evens = [n for n in cand if n % 2 == 0]
            if evens:
                cand.remove(random.choice(evens))
                odds = [n for n in all_numbers if n not in cand and n % 2 != 0]
                if odds:
                    cand.append(random.choice(odds))

    elif filter_name == "primos":
        prim_count = sum(1 for n in cand if n in PRIMOS)
        if prim_count < FILTERS["primos"]["min"]:
            non_primos = [n for n in cand if n not in PRIMOS]
            if non_primos:
                cand.remove(random.choice(non_primos))
                available_primos = [n for n in all_numbers if n not in cand and n in PRIMOS]
                if available_primos:
                    cand.append(random.choice(available_primos))
        elif prim_count > FILTERS["primos"]["max"]:
            primos_in = [n for n in cand if n in PRIMOS]
            if primos_in:
                cand.remove(random.choice(primos_in))
                available_non = [n for n in all_numbers if n not in cand and n not in PRIMOS]
                if available_non:
                    cand.append(random.choice(available_non))

    elif filter_name == "fibonacci":
        fib_count = sum(1 for n in cand if n in FIBONACCI)
        if fib_count < FILTERS["fibonacci"]["min"]:
            non_fib = [n for n in cand if n not in FIBONACCI]
            if non_fib:
                cand.remove(random.choice(non_fib))
                available_fib = [n for n in all_numbers if n not in cand and n in FIBONACCI]
                if available_fib:
                    cand.append(random.choice(available_fib))
        elif fib_count > FILTERS["fibonacci"]["max"]:
            fib_in = [n for n in cand if n in FIBONACCI]
            if fib_in:
                cand.remove(random.choice(fib_in))
                available_non = [n for n in all_numbers if n not in cand and n not in FIBONACCI]
                if available_non:
                    cand.append(random.choice(available_non))

    elif filter_name == "moldura":
        mold_count = sum(1 for n in cand if n in MOLDURA)
        if mold_count < FILTERS["moldura"]["min"]:
            non_mold = [n for n in cand if n not in MOLDURA]
            if non_mold:
                cand.remove(random.choice(non_mold))
                available_mold = [n for n in all_numbers if n not in cand and n in MOLDURA]
                if available_mold:
                    cand.append(random.choice(available_mold))
        elif mold_count > FILTERS["moldura"]["max"]:
            mold_in = [n for n in cand if n in MOLDURA]
            if mold_in:
                cand.remove(random.choice(mold_in))
                available_non = [n for n in all_numbers if n not in cand and n not in MOLDURA]
                if available_non:
                    cand.append(random.choice(available_non))

    elif filter_name == "consecutivos":
        s = sorted(cand)
        cons = sum(1 for i in range(len(s) - 1) if s[i + 1] == s[i] + 1)
        if cons < FILTERS["consecutivos"]["min"]:
            # Try to add a number adjacent to an existing one
            for num in cand:
                for neighbor in [num - 1, num + 1]:
                    if 1 <= neighbor <= 25 and neighbor not in cand:
                        # Remove a number that's not adjacent to anything
                        isolated = [n for n in cand if (n - 1) not in cand and (n + 1) not in cand]
                        if isolated:
                            cand.remove(random.choice(isolated))
                            cand.append(neighbor)
                            break
                else:
                    continue
                break

    return cand


# ── Main optimization ─────────────────────────────────────────────────────────

def optimize(
    probas: np.ndarray,
    last_draw: list[int] | None = None,
    n_candidates: int = N_CANDIDATES,
) -> list[int]:
    """Find the best 11 numbers combining neural probabilities with statistical filters.

    Returns the combination with the highest combined score:
    score = neural_prob_score * 0.7 + statistical_filter_score_normalized * 0.3

    Note: Higher weight on neural (0.7) since filters are soft constraints,
    not hard rules. The neural model already captures patterns well.
    """
    base_selection = sorted(np.argsort(probas)[::-1][:TARGET_COUNT] + 1)
    candidates = generate_candidates(probas, base_selection, n_candidates)

    # Include base selection itself as a candidate
    candidates.append(base_selection)

    # Neural probability score for base
    proba_sum = sum(probas[n - 1] for n in base_selection)
    total_filter_weight = sum(f["weight"] for f in FILTERS.values())

    best_combined = -float("inf")
    best_candidate = base_selection

    for cand in candidates:
        cand_proba = sum(probas[n - 1] for n in cand)
        cand_proba_norm = cand_proba / proba_sum if proba_sum > 0 else 0

        filter_score = score_candidate(cand, last_draw)
        # Normalize to [-1, 1] range
        filter_score_norm = filter_score / total_filter_weight

        # Combined score: neural dominates, filters provide gentle guidance
        combined = cand_proba_norm * 0.7 + (1.0 + filter_score_norm) * 0.3

        if combined > best_combined:
            best_combined = combined
            best_candidate = cand

    return sorted(best_candidate)
