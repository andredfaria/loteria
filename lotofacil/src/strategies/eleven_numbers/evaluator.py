"""Evaluator for the 11-numbers strategy.

Computes hit rates and other metrics specific to predicting 11 numbers.
"""

from __future__ import annotations

from typing import List

import numpy as np

from core.models import Draw, Prediction
from core.lottery import contar_acertos


class ElevenNumbersEvaluator:
    """Evaluates 11-numbers predictions against actual results."""

    def __init__(self):
        self.hits_history: List[int] = []

    def evaluate_single(self, prediction: Prediction, actual: List[int]) -> dict:
        """Evaluate a single prediction."""
        hits = contar_acertos(prediction.dezenas, actual)
        self.hits_history.append(hits)
        return {
            "hits": hits,
            "concurso_alvo": prediction.concurso_alvo,
            "dezenas_sugeridas": prediction.dezenas,
            "dezenas_reais": sorted(actual),
            "confianca": prediction.confianca_media,
        }

    def evaluate_backtest(self, draws: List[Draw], predictions: List[Prediction]) -> dict:
        """
        Evaluate multiple predictions against draws.

        Assumes predictions[i] is for draws[i+1] (or draws[-1] for last).
        """
        results = []
        for pred in predictions:
            actual_draw = next(
                (d for d in draws if d.concurso == pred.concurso_alvo),
                None,
            )
            if actual_draw:
                res = self.evaluate_single(pred, actual_draw.dezenas)
                results.append(res)

        if not results:
            return {"error": "No matching draws found for evaluation"}

        hits = [r["hits"] for r in results]
        return {
            "total_predictions": len(results),
            "mean_hits": float(np.mean(hits)),
            "hits_distribution": {
                str(i): hits.count(i) for i in range(min(hits), max(hits) + 1)
            },
            "hit_11_plus": sum(1 for h in hits if h >= 11),
            "hit_12_plus": sum(1 for h in hits if h >= 12),
            "hit_13_plus": sum(1 for h in hits if h >= 13),
            "hit_14_plus": sum(1 for h in hits if h >= 14),
            "hit_15": sum(1 for h in hits if h == 15),
            "best_hit": max(hits),
            "worst_hit": min(hits),
            "results": results,
        }

    def reset(self):
        """Clear evaluation history."""
        self.hits_history = []
