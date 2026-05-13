"""Confusion matrix computations for Lotofácil predictions."""
from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np

TOTAL_NUMBERS = 25


def confusion_per_number(results: List[dict]) -> dict:
    """
    Aggregate confusion matrix across 25 binary classifiers (did number n appear?).

    Args:
        results: list of {'predicted': List[int], 'actual': List[int], 'hits': int, 'probas': Optional[np.ndarray]}

    Returns:
        {
            'aggregate': {'TP': int, 'FP': int, 'TN': int, 'FN': int},
            'per_number': {n: {'TP': int, 'FP': int, 'TN': int, 'FN': int, 'F1': float}},
            'precision': float, 'recall': float, 'f1': float, 'accuracy': float,
        }
    """
    per = {n: {"TP": 0, "FP": 0, "TN": 0, "FN": 0} for n in range(1, TOTAL_NUMBERS + 1)}

    extra_fp = 0  # predictions outside 1-25 range
    for r in results:
        pred_set = set(r["predicted"])
        real_set = set(r["actual"])
        extra_fp += sum(1 for n in pred_set if n < 1 or n > TOTAL_NUMBERS)
        for n in range(1, TOTAL_NUMBERS + 1):
            p, a = n in pred_set, n in real_set
            if p and a:
                per[n]["TP"] += 1
            elif p:
                per[n]["FP"] += 1
            elif a:
                per[n]["FN"] += 1
            else:
                per[n]["TN"] += 1

    for n, cm in per.items():
        tp, fp, fn = cm["TP"], cm["FP"], cm["FN"]
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec = tp / (tp + fn) if (tp + fn) else 0.0
        cm["F1"] = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0

    if not results:
        return {
            "aggregate": {"TP": 0, "FP": 0, "TN": 0, "FN": 0},
            "per_number": per,
            "precision": 0.0,
            "recall": 0.0,
            "f1": 0.0,
            "accuracy": 0.0,
        }

    agg = {k: sum(per[n][k] for n in per) for k in ("TP", "FP", "TN", "FN")}
    agg["FP"] += extra_fp
    tp, fp, tn, fn = agg["TP"], agg["FP"], agg["TN"], agg["FN"]
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    total = tp + fp + tn + fn
    acc = (tp + tn) / total if total else 0.0

    return {
        "aggregate": agg,
        "per_number": per,
        "precision": prec,
        "recall": rec,
        "f1": f1,
        "accuracy": acc,
    }


def confusion_by_hits(results: List[dict]) -> dict:
    """
    Compare expected hit bucket (from probability mass) vs actual hit bucket.

    Expected hits for draw t = sum of p_i for i in actual draw.
    Actual hits = |predicted ∩ actual|.
    Buckets: 0 (less than 11), 11, 12, 13, 14, 15.

    Args:
        results: list of {'predicted': List[int], 'actual': List[int], 'probas': Optional[np.ndarray]}

    Returns:
        {
            'actual_distribution': {bucket: count},
            'expected_distribution': {bucket: count},
            'matrix': {(expected_bucket, actual_bucket): count},
        }
    """
    _buckets = [0, 11, 12, 13, 14, 15]

    def _bucket(hits: float) -> int:
        h = int(round(hits))
        return h if h >= 11 else 0

    actual_dist: Dict[int, int] = {b: 0 for b in _buckets}
    expected_dist: Dict[int, int] = {b: 0 for b in _buckets}
    matrix: Dict[tuple, int] = {}

    for r in results:
        actual_hits = len(set(r["predicted"]) & set(r["actual"]))
        ab = _bucket(actual_hits)
        actual_dist[ab] += 1

        probas = r.get("probas")
        if probas is not None:
            expected_hits = float(sum(probas[n - 1] for n in r["actual"]))
            eb = _bucket(expected_hits)
        else:
            eb = ab

        expected_dist[eb] += 1
        key = (eb, ab)
        matrix[key] = matrix.get(key, 0) + 1

    return {
        "actual_distribution": actual_dist,
        "expected_distribution": expected_dist,
        "matrix": matrix,
    }
