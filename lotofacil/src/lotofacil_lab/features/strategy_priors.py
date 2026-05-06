"""Strategy prior features: conformity of recent draws to the statistical hierarchy.

For each draw at index i, computes 8 scalars in [0, 1] measuring how often
the last K draws satisfied each strategic pattern. These are context signals
about the recent regime, not predictions for the next draw.

Hierarchy (docs/Hierarquia de Estratégias na Lotofácil):
  Nível 1: Soma (84%)
  Nível 2: Repetidos (70%), Par/Ímpar (56%)
  Nível 3: Moldura (55%), Primos, Fibonacci, Consecutivos, Ciclo
"""

from __future__ import annotations

from typing import List

import numpy as np

from lotofacil_lab.config import (
    TOTAL_NUMBERS, STRATEGY_PRIOR_WINDOW,
    STRATEGY_RANGES, PRIMOS, FIBONACCI, MOLDURA,
)

N_STRATEGY_FEATURES = 8


def _soma(dezenas: List[int]) -> int:
    return sum(dezenas)


def _repetidos(prev: List[int], cur: List[int]) -> int:
    return len(set(prev) & set(cur))


def _pares(dezenas: List[int]) -> int:
    return sum(1 for d in dezenas if d % 2 == 0)


def _moldura_count(dezenas: List[int]) -> int:
    return sum(1 for d in dezenas if d in MOLDURA)


def _primos_count(dezenas: List[int]) -> int:
    return sum(1 for d in dezenas if d in PRIMOS)


def _fibonacci_count(dezenas: List[int]) -> int:
    return sum(1 for d in dezenas if d in FIBONACCI)


def _consecutivos(dezenas: List[int]) -> int:
    sorted_dez = sorted(dezenas)
    count = sum(1 for a, b in zip(sorted_dez, sorted_dez[1:]) if b == a + 1)
    return count


def _ciclo_score(history: List[List[int]]) -> float:
    """Fraction of numbers that appeared in the last 4 draws (inverse absence)."""
    if not history:
        return 0.0
    recentes = set()
    for dez in history[-4:]:
        recentes.update(dez)
    return len(recentes) / TOTAL_NUMBERS


def _in_range(val: int, lo: int, hi: int) -> bool:
    return lo <= val <= hi


def build_strategy_priors_matrix(draws, k: int = STRATEGY_PRIOR_WINDOW) -> np.ndarray:
    """Shape (n, 8): strategy conformity scores for each draw.

    Each score = fraction of the last K draws satisfying the pattern.
    """
    n = len(draws)
    out = np.zeros((n, N_STRATEGY_FEATURES), dtype=np.float32)

    all_dezenas = [d.dezenas for d in draws]
    soma_lo, soma_hi = STRATEGY_RANGES["soma"]
    rep_lo, rep_hi = STRATEGY_RANGES["repetidos"]
    par_lo, par_hi = STRATEGY_RANGES["pares"]
    mol_lo, mol_hi = STRATEGY_RANGES["moldura"]
    primo_lo, primo_hi = STRATEGY_RANGES["primos"]
    fib_lo, fib_hi = STRATEGY_RANGES["fibonacci"]
    cons_lo, _ = STRATEGY_RANGES["consecutivos"]

    for i in range(n):
        start = max(0, i - k)
        window_dez = all_dezenas[start:i] if i > 0 else []

        if not window_dez:
            out[i] = 0.5  # neutral prior for warmup
            continue

        soma_ok = sum(_in_range(_soma(d), soma_lo, soma_hi) for d in window_dez)
        par_ok = sum(_in_range(_pares(d), par_lo, par_hi) for d in window_dez)
        mol_ok = sum(_in_range(_moldura_count(d), mol_lo, mol_hi) for d in window_dez)
        primo_ok = sum(_in_range(_primos_count(d), primo_lo, primo_hi) for d in window_dez)
        fib_ok = sum(_in_range(_fibonacci_count(d), fib_lo, fib_hi) for d in window_dez)
        cons_ok = sum(_consecutivos(d) >= cons_lo for d in window_dez)
        ciclo = _ciclo_score(window_dez)

        # Repetidos requires pairs — use sliding pairs
        rep_scores = []
        for j in range(1, len(window_dez)):
            rep_scores.append(_in_range(_repetidos(window_dez[j - 1], window_dez[j]), rep_lo, rep_hi))
        rep_ok_frac = sum(rep_scores) / len(rep_scores) if rep_scores else 0.5

        w = len(window_dez)
        out[i, 0] = soma_ok / w
        out[i, 1] = rep_ok_frac
        out[i, 2] = par_ok / w
        out[i, 3] = mol_ok / w
        out[i, 4] = primo_ok / w
        out[i, 5] = fib_ok / w
        out[i, 6] = cons_ok / w
        out[i, 7] = ciclo

    return out


def build_strategy_priors_sequences(draws, window: int) -> np.ndarray:
    """Shape (n - window, window, 8)."""
    flat = build_strategy_priors_matrix(draws)
    seqs = []
    for i in range(window, len(draws)):
        seqs.append(flat[i - window:i])
    return np.array(seqs, dtype=np.float32)
