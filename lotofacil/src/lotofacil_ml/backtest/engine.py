"""Walk-forward backtest engine — strict no-leakage guarantee."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np

from lotofacil_ml.config import BACKTEST_MIN_TRAIN, BACKTEST_RETRAIN_EVERY, BACKTEST_TRAIN_WINDOW
from lotofacil_ml.data.loader import Draw
from lotofacil_ml.models.base_model import BaseModel

logger = logging.getLogger(__name__)


@dataclass
class BacktestResult:
    concurso: int
    model_name: str
    jogo: List[int]
    resultado: List[int]
    hits: int
    probas: Optional[np.ndarray] = None


@dataclass
class BacktestSummary:
    model_name: str
    results: List[BacktestResult] = field(default_factory=list)

    @property
    def mean_hits(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.hits for r in self.results) / len(self.results)

    @property
    def hit_distribution(self) -> dict:
        dist = {k: 0 for k in range(0, 16)}
        for r in self.results:
            dist[r.hits] += 1
        return dist

    @property
    def rate_ge(self) -> dict:
        n = len(self.results)
        if n == 0:
            return {t: 0.0 for t in [11, 12, 13, 14, 15]}
        return {t: sum(1 for r in self.results if r.hits >= t) / n for t in [11, 12, 13, 14, 15]}


class BacktestEngine:
    """
    Walk-forward backtest engine.

    For each test draw at index idx in [start_idx, end_idx):
      - train_draws = draws[max(0, idx - train_window) : idx]  <- never includes idx
      - model.fit(train_draws)   (only on retrain epochs)
      - jogo = model.select_top_15()
      - hits = |set(jogo) & set(draws[idx].dezenas)|
    """

    def __init__(
        self,
        model: BaseModel,
        train_window: int = BACKTEST_TRAIN_WINDOW,
        retrain_every: int = BACKTEST_RETRAIN_EVERY,
        min_train: int = BACKTEST_MIN_TRAIN,
    ):
        self.model = model
        self.train_window = train_window
        self.retrain_every = retrain_every
        self.min_train = min_train
        self._last_retrain_idx: Optional[int] = None

    def run(
        self,
        draws: List[Draw],
        start_idx: Optional[int] = None,
        end_idx: Optional[int] = None,
        capture_probas: bool = False,
    ) -> List[BacktestResult]:
        """
        Run walk-forward backtest.

        Args:
            draws: full sorted draw history
            start_idx: first test index (default: train_window)
            end_idx: last test index exclusive (default: len(draws))

        Returns:
            List of BacktestResult, one per test draw.
        """
        n = len(draws)
        s = start_idx if start_idx is not None else self.train_window
        e = end_idx if end_idx is not None else n

        if s >= n or e > n or s >= e:
            logger.warning("Invalid range [%d, %d) for %d draws", s, e, n)
            return []

        results = []
        self._last_retrain_idx = None

        for idx in range(s, e):
            train_start = max(0, idx - self.train_window)
            train_draws = draws[train_start:idx]  # strictly excludes idx

            if len(train_draws) < self.min_train:
                logger.debug("Skipping idx=%d: only %d train draws", idx, len(train_draws))
                continue

            # Retrain on first iteration or every retrain_every steps
            needs_retrain = (
                self._last_retrain_idx is None
                or (idx - self._last_retrain_idx) >= self.retrain_every
            )
            if needs_retrain:
                logger.debug("Retraining at idx=%d on %d draws", idx, len(train_draws))
                self.model.fit(train_draws)
                self._last_retrain_idx = idx

            jogo = self.model.select_top_15()
            probas = self.model.predict_proba() if capture_probas else None
            resultado = draws[idx].dezenas
            hits = len(set(jogo) & set(resultado))

            results.append(BacktestResult(
                concurso=draws[idx].concurso,
                model_name=self.model.name,
                jogo=jogo,
                resultado=resultado,
                hits=hits,
                probas=probas,
            ))

        return results
