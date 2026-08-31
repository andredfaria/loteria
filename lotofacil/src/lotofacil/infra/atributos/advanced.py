"""Advanced feature functions for Lotofácil ML pipeline."""

from __future__ import annotations

import logging
import math
from collections import Counter
from typing import Dict, List

from lotofacil.dominio.entidades import Sorteio as Draw
from lotofacil.infra.atributos.base import freq_k, atraso as calc_atraso

_NUMBERS = list(range(1, 26))
_FAIXAS = {1: range(1, 6), 2: range(6, 11), 3: range(11, 16), 4: range(16, 21), 5: range(21, 26)}

logger = logging.getLogger(__name__)

# Below this mean expected(n, m), the lift is dominated by integer-count
# noise (minimum step of 1/expected), not real statistical signal. See the
# honest note in coocorrencia_score.
_MIN_RELIABLE_EXPECTED = 5.0

# `coocorrencia_score` is called once per dataset row — thousands of times in
# a single training run. The low-expected condition depends only on (k, top)
# and the lottery's density, never on idx, so warning on every call would emit
# ~2800 identical lines per run: the warning would get silenced and nobody
# would read it. Emit once per parameter combination, per process.
_low_expected_warned: set[tuple[int, int]] = set()


def _warn_low_expected(k: int, top: int, mean_expected: float) -> None:
    if mean_expected >= _MIN_RELIABLE_EXPECTED:
        return
    key = (k, top)
    if key in _low_expected_warned:
        return
    _low_expected_warned.add(key)
    logger.warning(
        "coocorrencia_score: mean expected=%.2f (< %.0f) with k=%d, top=%d -- "
        "lift dominated by counting noise, not real dependency "
        "(see HONEST NOTE in the docstring). Warned once per process.",
        mean_expected, _MIN_RELIABLE_EXPECTED, k, top,
    )




def coocorrencia_score(
    draws: List[Draw], idx: int, k: int = 30, top: int = 10, alpha: float = 1.0
) -> Dict[int, float]:
    """
    Affinity of each number N with the `top` hottest numbers in the k-draw
    window, measured as lift over independence with additive (Laplace)
    smoothing:

        lift(n, m) = (observed(n, m) + alpha) / (expected(n, m) + alpha)
        expected(n, m) = window_size * freq(n) * freq(m)

    The score for N is the mean lift between N and each of the `top` most
    frequent numbers in the window.

    HONEST NOTE: the neutral value under statistical independence is 1.0 by
    construction -- which is why "no evidence" (empty window, or the number
    never appeared in the window) also returns 1.0 here, never 0.0, which
    would encode "never seen this number" as "maximum anti-affinity". But the
    ESTIMATOR has a known, measured negative bias that smoothing alone does
    not remove: with truly independent uniform draws (k=30, top=10, 7000
    samples, seed=99), the measured mean was 0.979 (a 0.021 deviation below
    1.0), not exactly 1.0. The bias comes from Jensen's inequality --
    E[obs/exp] < E[obs]/E[exp] when `exp` is small. Lotofácil (15 of 25
    numbers drawn) is the densest of the four lotteries this formula is used
    in, so `expected(n, m)` is comfortably above 5 at the default k/top and
    the bias stays small; do not treat 0.979 as "close enough to not
    matter" without checking it against the actual number if k/top change.

    In sparser lotteries (few numbers drawn out of a large universe),
    `expected(n, m)` can be well under 1 in a window of a few dozen draws.
    Since `observed` is an integer count, the raw (unsmoothed) lift can only
    take multiples of `1/expected` -- a single observed co-occurrence would
    make the lift jump from 0 to several units, turning the feature into
    rescaled counting noise rather than a continuous signal. The `alpha`
    smoothing (default 1.0) reduces this bias but does not eliminate it;
    with a very low expected value, do not expect a fine-grained signal --
    expect something close to 1.0 most of the time, with occasional discrete
    jumps. A WARNING is logged when the window's mean expected value falls
    below a confidence threshold (see `_MIN_RELIABLE_EXPECTED`); do not read
    high values as evidence that "these numbers are drawn together" even
    when the warning does not fire.
    """
    window = draws[max(0, idx - k):idx]
    # 1.0 is the neutral value under independence (see HONEST NOTE), not 0.0:
    # "no evidence" (empty window, or the number never appeared in the
    # window) is not the same thing as "maximum anti-affinity".
    scores = {n: 1.0 for n in _NUMBERS}
    n_window = len(window)
    if n_window == 0:
        return scores

    freq = freq_k(draws, idx, k)
    top_dezenas = sorted(_NUMBERS, key=lambda n: freq[n], reverse=True)[:top]
    top_set = set(top_dezenas)

    # Count pairs only against the `top` hot numbers (not the full
    # _NUMBERS x _NUMBERS matrix) -- much cheaper since build_dataset calls
    # this once per dataset row.
    pair_counts = {m: Counter() for m in top_dezenas}
    for d in window:
        dez_set = set(d.dezenas)
        hot_in_draw = dez_set & top_set
        if not hot_in_draw:
            continue
        for m in hot_in_draw:
            pair_counts[m].update(n for n in dez_set if n != m)

    expecteds: List[float] = []
    for n in _NUMBERS:
        lifts = []
        for m in top_dezenas:
            if m == n or freq[n] <= 0 or freq[m] <= 0:
                continue
            esperado = n_window * freq[n] * freq[m]
            observado = pair_counts[m][n]
            lifts.append((observado + alpha) / (esperado + alpha))
            expecteds.append(esperado)
        scores[n] = sum(lifts) / len(lifts) if lifts else 1.0

    if expecteds:
        mean_expected = sum(expecteds) / len(expecteds)
        _warn_low_expected(k, top, mean_expected)

    return scores


def trend_score(draws: List[Draw], idx: int) -> Dict[int, float]:
    """
    freq_k5 - freq_k20: positive = heating up, negative = cooling down.
    """
    f5 = freq_k(draws, idx, k=5)
    f20 = freq_k(draws, idx, k=20)
    return {n: f5[n] - f20[n] for n in _NUMBERS}


def volatilidade_score(
    draws: List[Draw], idx: int, outer_k: int = 50, inner_k: int = 10
) -> Dict[int, float]:
    """
    Std dev of frequency of N computed in non-overlapping inner_k windows
    inside the outer_k draws before idx.
    """
    window = draws[max(0, idx - outer_k):idx]
    n_windows = max(1, len(window) // inner_k)
    scores = {n: [] for n in _NUMBERS}

    for w in range(n_windows):
        sub = window[w * inner_k:(w + 1) * inner_k]
        if not sub:
            continue
        counts = Counter()
        for d in sub:
            counts.update(d.dezenas)
        for n in _NUMBERS:
            scores[n].append(counts[n] / len(sub))

    result = {}
    for n in _NUMBERS:
        vals = scores[n]
        if len(vals) < 2:
            result[n] = 0.0
        else:
            mean = sum(vals) / len(vals)
            # population std dev (consistent with base.py stats_soma)
            result[n] = math.sqrt(sum((v - mean) ** 2 for v in vals) / len(vals))
    return result


def faixa_dominante(draws: List[Draw], idx: int) -> int:
    """Faixa (1-5) with most numbers in the draw immediately before idx."""
    if idx == 0:
        return 1
    dez = set(draws[idx - 1].dezenas)
    counts = {f: sum(1 for n in dez if n in rng) for f, rng in _FAIXAS.items()}
    # ties broken by lowest faixa number (dict insertion order, keys 1-5)
    return max(counts, key=counts.get)


def par_quente_score(draws: List[Draw], idx: int, k: int = 30) -> float:
    """
    Count how many of the top-10 most frequent numbers (in window k)
    also have atraso <= 3 (recently appeared = 'hot').
    """
    fk = freq_k(draws, idx, k=k)
    top10 = sorted(fk, key=fk.get, reverse=True)[:10]
    at = calc_atraso(draws, idx, max_atraso=20)
    return float(sum(1 for n in top10 if at[n] <= 3))
