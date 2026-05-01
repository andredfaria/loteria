"""ML approach for 11-numbers strategy.

Uses FeatureBuilder + MLEnsemble for prediction.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

import numpy as np

from core.models import Draw
from core.config import OUTPUT_MODELS
from data.preprocessor import LotofacilPreprocessor
from features.builder import FeatureBuilder
from models.ensemble import MLModel


class MLApproach:
    """Predicts using LightGBM multi-output classifier."""

    def __init__(self):
        self._model = MLModel()
        self._fitted = False

    def fit(self, draws: List[Draw]) -> None:
        self._model.fit(draws)
        self._fitted = True

    def predict_proba(self, draws: List[Draw]) -> np.ndarray:
        if not self._fitted:
            raise RuntimeError("Approach not fitted. Call fit() first.")
        return self._model.predict_proba_for_draws(draws)

    def save(self, path: Path | None = None) -> None:
        if path is None:
            path = OUTPUT_MODELS / "ml_ensemble_11numbers.joblib"
        self._model.save(path)

    def load(self, path: Path | None = None) -> None:
        if path is None:
            path = OUTPUT_MODELS / "ml_ensemble_11numbers.joblib"
        self._model.load(path)
        self._fitted = True

    @property
    def name(self) -> str:
        return "ml"

    @property
    def is_fitted(self) -> bool:
        return self._fitted
