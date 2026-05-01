"""ML model: LightGBM with multi-output support."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

import joblib
import numpy as np
from lightgbm import LGBMClassifier
from sklearn.multioutput import MultiOutputClassifier

from core.config import RANDOM_SEED
from core.models import Draw
from features.builder import FeatureBuilder
from models.base import BaseModel


class MLModel(BaseModel):
    """LightGBM multi-output classifier for Lotofácil prediction."""

    def __init__(self):
        base = LGBMClassifier(
            n_estimators=100,
            max_depth=6,
            min_samples_leaf=10,
            random_state=RANDOM_SEED,
            verbose=-1,
            n_jobs=1,
        )
        self._model = MultiOutputClassifier(base, n_jobs=1)
        self._fitted = False
        self._feature_builder = FeatureBuilder()

    def fit(self, draws: List[Draw]) -> None:
        builder = FeatureBuilder()
        X, y = builder.build_dataset(draws)
        self._model.fit(X, y)
        self._feature_builder = builder
        self._fitted = True

    def predict_proba_for_draws(self, draws: List[Draw]) -> np.ndarray:
        """Get probabilities for the next draw given current draws."""
        if not self._fitted:
            raise RuntimeError("Model not fitted. Call fit() first.")

        builder = FeatureBuilder()
        X_inf = builder.build_inference(draws)
        p_list = self._model.predict_proba(X_inf)

        probas = np.zeros(25, dtype=np.float64)
        for i, p in enumerate(p_list):
            probas[i] = p[0, 1] if p.ndim == 2 else p[1]

        if probas.sum() > 0:
            probas /= probas.sum()

        return probas

    def predict_proba(self) -> np.ndarray:
        if not self._fitted:
            raise RuntimeError("Model not fitted. Call fit() first.")
        return np.zeros(25, dtype=np.float64)

    def save(self, path: Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({"model": self._model}, path)
        meta = {"feature_names": self._feature_builder.feature_names}
        with open(path.with_suffix(".meta.json"), "w") as f:
            json.dump(meta, f)

    def load(self, path: Path) -> None:
        data = joblib.load(path)
        self._model = data["model"]
        meta_path = path.with_suffix(".meta.json")
        if meta_path.exists():
            with open(meta_path) as f:
                meta = json.load(f)
            self._feature_builder.feature_names = meta.get("feature_names", [])
            self._feature_builder.n_features = len(self._feature_builder.feature_names)
        self._fitted = True

    @property
    def name(self) -> str:
        return "ml"
