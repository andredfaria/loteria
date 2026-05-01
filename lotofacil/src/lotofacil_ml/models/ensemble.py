"""Ensemble predictor combining all sub-models by weighted average."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List

import numpy as np

from lotofacil_ml.config import MODELS_DIR, TOTAL_NUMBERS
from lotofacil_ml.data.loader import Draw
from lotofacil_ml.models.base_model import BaseModel
from lotofacil_ml.models.frequency_ensemble import FrequencyEnsembleModel
from lotofacil_ml.models.ml_model import MLEnsembleModel
from lotofacil_ml.models.probabilistic import ProbabilisticModel

logger = logging.getLogger(__name__)

_DEFAULT_WEIGHTS = {"frequency": 0.20, "ml": 0.50, "probabilistic": 0.30}


class EnsemblePredictor:
    """Weighted combination of FrequencyEnsembleModel + MLEnsembleModel + ProbabilisticModel.

    Intentionally does NOT inherit BaseModel — it orchestrates sub-models
    rather than implementing a single model's interface.
    """

    def __init__(
        self,
        models_dir: Path = MODELS_DIR,
        weights: dict[str, float] | None = None,
    ):
        self.models_dir = Path(models_dir)
        self.weights = weights or _DEFAULT_WEIGHTS
        self.frequency = FrequencyEnsembleModel()
        self.ml = MLEnsembleModel()
        self.probabilistic = ProbabilisticModel()
        self._fitted = False

    @property
    def name(self) -> str:
        return "ensemble"

    def fit(self, draws: List[Draw]) -> None:
        logger.info("Fitting EnsemblePredictor on %d draws", len(draws))
        self.frequency.fit(draws)
        self.ml.fit(draws)
        self.probabilistic.fit(draws)
        self._fitted = True

    def predict_proba(self) -> np.ndarray:
        if not self._fitted:
            return np.full(TOTAL_NUMBERS, 1.0 / TOTAL_NUMBERS, dtype=np.float32)
        p_freq = self.frequency.predict_proba()
        p_ml = self.ml.predict_proba()
        p_prob = self.probabilistic.predict_proba()
        combined = (
            self.weights.get("frequency", 0.2) * p_freq
            + self.weights.get("ml", 0.5) * p_ml
            + self.weights.get("probabilistic", 0.3) * p_prob
        )
        return combined.astype(np.float32)

    def select_top_15(self) -> List[int]:
        p = self.predict_proba()
        indices = np.argsort(p)[::-1][:15]
        return sorted(int(i + 1) for i in indices)

    def save(self) -> None:
        self.frequency.save(self.models_dir)
        self.ml.save(self.models_dir)
        self.probabilistic.save(self.models_dir)

    def load(self) -> None:
        loaded = 0
        for model, attr in [(self.frequency, "frequency"), (self.ml, "ml"), (self.probabilistic, "probabilistic")]:
            try:
                model.load(self.models_dir)
                loaded += 1
            except Exception as exc:
                logger.warning("%s load failed: %s", attr, exc)
        if loaded == 0:
            logger.error("EnsemblePredictor: all sub-model loads failed — predictions will use uniform fallback")
        self._fitted = loaded > 0
