"""Walk-forward backtest engine for Lotofácil strategies."""

from __future__ import annotations

import logging
from typing import List

from core.models import Draw
from evaluation.metrics import hits_distribution, mean_hits, hit_rate_at, roi

logger = logging.getLogger(__name__)


class BacktestEngine:
    """Walk-forward backtest: train on window, predict next, slide."""

    def __init__(self, strategy, train_window: int = 300, retrain_every: int = 50):
        self.strategy = strategy
        self.train_window = train_window
        self.retrain_every = retrain_every
        self.results: List[dict] = []

    def run(self, draws: List[Draw]) -> dict:
        """
        Run walk-forward backtest.

        For each draw after train_window, predict and compare with actual.
        Retrains every retrain_every draws.
        """
        self.results = []
        n = len(draws)
        min_start = self.train_window

        if n <= min_start:
            raise ValueError(f"Need more than {min_start} draws for backtest, got {n}")

        last_train_idx = min_start
        model_fitted = False

        for idx in range(min_start, n):
            if idx >= last_train_idx + self.retrain_every:
                model_fitted = False
                last_train_idx = idx

            train_draws = draws[:idx]
            actual = draws[idx]

            try:
                if not model_fitted:
                    prediction = self.strategy.predict(train_draws, approach="all")
                    model_fitted = True
                else:
                    prediction = self.strategy.predict(train_draws, approach="all")

                hits = self.strategy.evaluate(prediction, actual.dezenas)
                self.results.append({
                    "concurso": actual.concurso,
                    "hits": hits,
                    "predicted": prediction.dezenas,
                    "actual": actual.dezenas,
                    "confianca": prediction.confianca_media,
                })
            except Exception as e:
                logger.warning("Backtest failed for concurso %d: %s", actual.concurso, e)

        return self.summarize()

    def summarize(self) -> dict:
        """Summarize backtest results."""
        if not self.results:
            return {"error": "No results to summarize"}

        all_hits = [r["hits"] for r in self.results]
        n_games = len(all_hits)

        return {
            "total_draws_tested": n_games,
            "mean_hits": mean_hits(all_hits),
            "hits_distribution": hits_distribution(all_hits),
            "hit_11_plus": sum(1 for h in all_hits if h >= 11),
            "hit_12_plus": sum(1 for h in all_hits if h >= 12),
            "hit_13_plus": sum(1 for h in all_hits if h >= 13),
            "hit_14_plus": sum(1 for h in all_hits if h >= 14),
            "hit_15": sum(1 for h in all_hits if h == 15),
            "hit_rate_11": hit_rate_at(all_hits, 11),
            "hit_rate_12": hit_rate_at(all_hits, 12),
            "hit_rate_13": hit_rate_at(all_hits, 13),
            "roi_percent": roi(all_hits, n_games),
            "best_hit": max(all_hits),
            "worst_hit": min(all_hits),
            "results": self.results,
        }
