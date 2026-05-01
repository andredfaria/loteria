"""Evaluation metrics for Lotofácil predictions."""

from __future__ import annotations

from typing import List

import numpy as np

from core.config import COST_PER_GAME, PRIZE_TABLE
from core.lottery import contar_acertos


def count_hits(predictions: list, actual: list) -> int:
    """Count hits between a prediction and actual result."""
    return contar_acertos(predictions, actual)


def hits_distribution(all_hits: list[int]) -> dict[int, int]:
    """Distribution of hit counts."""
    dist = {}
    for h in all_hits:
        dist[h] = dist.get(h, 0) + 1
    return dict(sorted(dist.items()))


def mean_hits(all_hits: list[int]) -> float:
    return float(np.mean(all_hits)) if all_hits else 0.0


def hit_rate_at(all_hits: list[int], threshold: int) -> float:
    """Percentage of predictions with hits >= threshold."""
    if not all_hits:
        return 0.0
    return sum(1 for h in all_hits if h >= threshold) / len(all_hits)


def roi(all_hits: list[int], n_games: int) -> float:
    """Return on investment percentage."""
    if not n_games:
        return 0.0
    total_cost = n_games * COST_PER_GAME
    total_prize = sum(PRIZE_TABLE.get(h, 0) for h in all_hits)
    return ((total_prize - total_cost) / total_cost * 100) if total_cost > 0 else 0.0


def precision_at_k(probas: np.ndarray, actual: list[int], k: int = 11) -> float:
    """Precision: fraction of top-k predicted that are in actual."""
    top_k = np.argsort(probas)[::-1][:k]
    top_k_set = {int(i + 1) for i in top_k}
    actual_set = set(actual)
    return len(top_k_set & actual_set) / k


def recall_at_k(probas: np.ndarray, actual: list[int], k: int = 11) -> float:
    """Recall: fraction of actual that are in top-k predicted."""
    top_k = np.argsort(probas)[::-1][:k]
    top_k_set = {int(i + 1) for i in top_k}
    actual_set = set(actual)
    return len(top_k_set & actual_set) / len(actual_set) if actual_set else 0.0
