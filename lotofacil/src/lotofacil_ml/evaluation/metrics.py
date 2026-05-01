"""Lottery-specific evaluation metrics."""

import logging
import random
from typing import Dict, List

import numpy as np

from lotofacil_ml.config import HIT_THRESHOLDS, NUMBERS_PER_DRAW, RANDOM_SEED, TOTAL_NUMBERS

logger = logging.getLogger(__name__)


def _count_hits(predicted: List[int], actual: List[int]) -> int:
    return len(set(predicted) & set(actual))


class LotofacilMetrics:

    @staticmethod
    def distribution_of_hits(results: List[dict]) -> Dict[int, int]:
        """
        Count how many predictions achieved each hit level (11–15).
        Args:
            results: list of {"predicted": [int], "actual": [int], "hits": int}
        """
        dist = {t: 0 for t in HIT_THRESHOLDS}
        for r in results:
            hits = r.get("hits", _count_hits(r["predicted"], r["actual"]))
            if hits in dist:
                dist[hits] += 1
        return dist

    @staticmethod
    def mean_accuracy(results: List[dict]) -> float:
        """Average number of correct predictions per game."""
        if not results:
            return 0.0
        totals = [
            r.get("hits", _count_hits(r["predicted"], r["actual"]))
            for r in results
        ]
        return float(np.mean(totals))

    @staticmethod
    def recall_precision(results: List[dict]) -> Dict[str, float]:
        """
        Recall = fraction of actual numbers correctly predicted.
        Precision = fraction of predicted numbers that are in actual.
        """
        if not results:
            return {"recall": 0.0, "precision": 0.0}
        recalls, precisions = [], []
        for r in results:
            hits = _count_hits(r["predicted"], r["actual"])
            recalls.append(hits / NUMBERS_PER_DRAW)
            precisions.append(hits / len(r["predicted"]) if r["predicted"] else 0.0)
        return {
            "recall": float(np.mean(recalls)),
            "precision": float(np.mean(precisions)),
        }

    @staticmethod
    def vs_random_baseline(results: List[dict], n_simulations: int = 1000) -> Dict[str, float]:
        """
        Compare model mean accuracy against a random-selection baseline.
        Returns: model_mean, random_mean, improvement_pct, p_value (approximated).
        """
        rng = random.Random(RANDOM_SEED)
        all_numbers = list(range(1, TOTAL_NUMBERS + 1))

        model_hits = [
            r.get("hits", _count_hits(r["predicted"], r["actual"]))
            for r in results
        ]
        model_mean = float(np.mean(model_hits)) if model_hits else 0.0

        sim_means = []
        for _ in range(n_simulations):
            sim_hits = []
            for r in results:
                rand_pick = rng.sample(all_numbers, NUMBERS_PER_DRAW)
                sim_hits.append(_count_hits(rand_pick, r["actual"]))
            sim_means.append(float(np.mean(sim_hits)))

        random_mean = float(np.mean(sim_means))
        # p-value: proportion of simulations that beat the model
        p_value = float(np.mean([1 if m >= model_mean else 0 for m in sim_means]))
        improvement = ((model_mean - random_mean) / random_mean * 100) if random_mean else 0.0

        return {
            "model_mean": model_mean,
            "random_mean": random_mean,
            "improvement_pct": round(improvement, 2),
            "p_value": round(p_value, 4),
        }


def rmse_expected_hits(results: List[dict]) -> float:
    """
    RMSE between expected_hits (probability mass on correct numbers) and actual_hits.

    expected_hits_t = Σ probas[n-1] for n in actual_t
    actual_hits_t   = |predicted_t ∩ actual_t|

    Args:
        results: list of {'predicted': List[int], 'actual': List[int],
                          'hits': int, 'probas': Optional[np.ndarray shape (25,)]}
    """
    if not results:
        return 0.0
    errors = []
    for r in results:
        actual_hits = r.get("hits", _count_hits(r["predicted"], r["actual"]))
        probas = r.get("probas")
        if probas is not None:
            expected = float(sum(probas[n - 1] for n in r["actual"]))
        else:
            expected = float(actual_hits)
        errors.append((expected - actual_hits) ** 2)
    return float(np.sqrt(np.mean(errors)))


def mae_expected_hits(results: List[dict]) -> float:
    """
    MAE between expected_hits and actual_hits. Same semantics as rmse_expected_hits.
    """
    if not results:
        return 0.0
    errors = []
    for r in results:
        actual_hits = r.get("hits", _count_hits(r["predicted"], r["actual"]))
        probas = r.get("probas")
        if probas is not None:
            expected = float(sum(probas[n - 1] for n in r["actual"]))
        else:
            expected = float(actual_hits)
        errors.append(abs(expected - actual_hits))
    return float(np.mean(errors))


def roc_auc_per_number(results: List[dict]) -> Dict[str, object]:
    """
    ROC-AUC per number using raw probability scores.

    For each number n (1–25): AUC of score=probas[n-1] vs label=(n in actual).
    Requires at least 2 draws and both positive + negative labels per number.

    Args:
        results: list of {'actual': List[int], 'probas': Optional[np.ndarray shape (25,)]}

    Returns:
        {'mean': float, 'std': float, 'per_number': {n: float for n in 1..25}}
    """
    from sklearn.metrics import roc_auc_score

    _default = {"mean": 0.5, "std": 0.0, "per_number": {n: 0.5 for n in range(1, 26)}}
    if not results:
        return _default

    filtered = [r for r in results if r.get("probas") is not None]
    if not filtered:
        return _default

    labels: Dict[int, list] = {n: [] for n in range(1, 26)}
    scores: Dict[int, list] = {n: [] for n in range(1, 26)}

    for r in filtered:
        actual_set = set(r["actual"])
        probas = r["probas"]
        for n in range(1, 26):
            labels[n].append(1 if n in actual_set else 0)
            scores[n].append(float(probas[n - 1]))

    aucs: Dict[int, float] = {}
    for n in range(1, 26):
        y = labels[n]
        if len(set(y)) < 2:
            aucs[n] = 0.5
            continue
        try:
            aucs[n] = float(roc_auc_score(y, scores[n]))
        except Exception:
            aucs[n] = 0.5

    vals = list(aucs.values())
    return {
        "mean": float(np.mean(vals)),
        "std": float(np.std(vals)),
        "per_number": aucs,
    }
