"""Baseline game generators for backtest comparison."""

from __future__ import annotations

import random
from typing import List

from lotofacil_ml.config import RANDOM_SEED
from lotofacil_ml.data.loader import Draw

_ALL = list(range(1, 26))
_rng = random.Random(RANDOM_SEED)


def random_game() -> List[int]:
    """15 numbers drawn uniformly at random from 1-25."""
    return sorted(_rng.sample(_ALL, 15))


def freq_historical_game(draws: List[Draw]) -> List[int]:
    """Top-15 numbers by accumulated frequency up to the current draw."""
    counts = {n: 0 for n in _ALL}
    for d in draws:
        for n in d.dezenas:
            counts[n] += 1
    top15 = sorted(counts, key=counts.get, reverse=True)[:15]
    return sorted(top15)


def delay_game(draws: List[Draw]) -> List[int]:
    """Top-15 numbers with highest delay (least recently drawn)."""
    last_seen = {n: -1 for n in _ALL}
    for i, d in enumerate(draws):
        for n in d.dezenas:
            last_seen[n] = i
    n_total = len(draws)
    delay = {n: n_total - last_seen[n] - 1 for n in _ALL}
    top15 = sorted(delay, key=delay.get, reverse=True)[:15]
    return sorted(top15)
