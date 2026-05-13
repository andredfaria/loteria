"""ML approach for 11-numbers strategy.

Uses FeatureBuilder + MLEnsemble for prediction.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

import numpy as np

from lotofacil.dominio.entidades import Draw
from lotofacil.infra.config import OUTPUT_MODELS
from lotofacil.infra.dados.preprocessador import LotofacilPreprocessor
from lotofacil.infra.atributos.builder import FeatureBuilder
from lotofacil.infra.modelos.ml_model import MLEnsembleModel


class MLApproach:
    """Predicts using ML ensemble (RF+XGB+LightGBM)."""

    def __init__(self):
        self._model = MLEnsembleModel()
        self._fitted = False

    def fit(self, draws: List[Draw]) -> None:
        self._model.fit(draws)
        self._fitted = True

    def predict_proba(self, draws: List[Draw]) -> np.ndarray:
        if not self._fitted:
            raise RuntimeError("Approach not fitted. Call fit() first.")
        return self._model.predict_proba()

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
