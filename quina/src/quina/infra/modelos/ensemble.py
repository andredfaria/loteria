from __future__ import annotations

import logging
from pathlib import Path
from typing import List

import numpy as np

from quina.infra.config import MODELOS_DIR, TOTAL_NUMEROS
from quina.dominio.entidades import Sorteio as Draw
from quina.infra.modelos.frequency_ensemble import FrequencyEnsembleModel
from quina.infra.modelos.ml_model import MLEnsembleModel
from quina.infra.modelos.probabilistic import ProbabilisticModel

logger = logging.getLogger(__name__)

_DEFAULT_WEIGHTS = {"frequency": 0.20, "ml": 0.50, "probabilistic": 0.30}


class EnsemblePredictor:
    def __init__(
        self,
        models_dir: Path = MODELOS_DIR,
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
        if not self._try_load():
            self.frequency.fit(draws)
            self.ml.fit(draws)
            self.probabilistic.fit(draws)
        self._fitted = True

    def _try_load(self) -> bool:
        loaded = 0
        for model in [self.frequency, self.ml, self.probabilistic]:
            try:
                model.load(self.models_dir)
                loaded += 1
            except Exception:
                pass
        return loaded > 0

    def predict_proba(self) -> np.ndarray:
        if not self._fitted:
            return np.full(TOTAL_NUMEROS, 1.0 / TOTAL_NUMEROS, dtype=np.float32)
        p_freq = self.frequency.predict_proba()
        p_ml = self.ml.predict_proba()
        p_prob = self.probabilistic.predict_proba()
        combined = (
            self.weights.get("frequency", 0.2) * p_freq
            + self.weights.get("ml", 0.5) * p_ml
            + self.weights.get("probabilistic", 0.3) * p_prob
        )
        return combined.astype(np.float32)

    def select_top_5(self) -> List[int]:
        p = self.predict_proba()
        indices = np.argsort(p)[::-1][:5]
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