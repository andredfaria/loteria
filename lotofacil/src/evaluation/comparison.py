"""Compare approaches within a strategy."""

from __future__ import annotations

from typing import List

from core.models import Draw
from evaluation.backtest import BacktestEngine


def compare_approaches(strategy, draws: List[Draw]) -> dict:
    """
    Run backtest for each approach and compare results.
    """
    comparison = {}
    for approach in strategy.approaches:
        if approach == "all":
            continue
        try:
            engine = BacktestEngine(strategy, train_window=100, retrain_every=30)
            result = engine.run(draws)
            comparison[approach] = {
                "mean_hits": result.get("mean_hits", 0),
                "hit_11_plus": result.get("hit_11_plus", 0),
                "hit_12_plus": result.get("hit_12_plus", 0),
                "roi_percent": result.get("roi_percent", 0),
                "best_hit": result.get("best_hit", 0),
            }
        except Exception as e:
            comparison[approach] = {"error": str(e)}

    return comparison
