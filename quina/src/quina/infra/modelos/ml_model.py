from __future__ import annotations

import logging
from pathlib import Path
from typing import List

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.multioutput import MultiOutputClassifier

from quina.dominio.entidades import Sorteio as Draw
from quina.infra.config import TOTAL_NUMEROS, RANDOM_SEED, RF_N_ESTIMATORS, RF_MAX_DEPTH, RF_MIN_SAMPLES_LEAF
from quina.infra.atributos.builder import FeatureBuilder
from quina.infra.modelos.base_model import BaseModel

logger = logging.getLogger(__name__)


def _build_voter() -> VotingClassifier:
    estimators = [
        ("rf", RandomForestClassifier(
            n_estimators=100, max_depth=8,
            min_samples_leaf=RF_MIN_SAMPLES_LEAF,
            random_state=RANDOM_SEED, n_jobs=-1,
        ))
    ]
    try:
        from xgboost import XGBClassifier
        estimators.append(("xgb", XGBClassifier(
            n_estimators=100, max_depth=4, learning_rate=0.1,
            random_state=RANDOM_SEED, eval_metric="logloss", verbosity=0,
        )))
    except ImportError:
        logger.warning("xgboost not installed — skipping XGBClassifier")

    try:
        from lightgbm import LGBMClassifier
        estimators.append(("lgbm", LGBMClassifier(
            n_estimators=100, max_depth=4, learning_rate=0.1,
            random_state=RANDOM_SEED, verbosity=-1,
        )))
    except ImportError:
        logger.warning("lightgbm not installed — skipping LGBMClassifier")

    return VotingClassifier(estimators=estimators, voting="soft", n_jobs=-1)


class MLEnsembleModel(BaseModel):
    def __init__(self):
        self._model: MultiOutputClassifier | None = None
        self._builder = FeatureBuilder()
        self._latest_x: np.ndarray | None = None
        self._fitted = False

    @property
    def name(self) -> str:
        return "ml"

    def fit(self, draws: List[Draw]) -> None:
        logger.info("Building features for MLEnsembleModel on %d draws", len(draws))
        X, y = self._builder.build_dataset(draws)
        logger.info("Training MLEnsembleModel X=%s y=%s", X.shape, y.shape)
        voter = _build_voter()
        self._model = MultiOutputClassifier(voter, n_jobs=1)
        self._model.fit(X, y)
        self._latest_x = self._builder.build_inference(draws)
        self._fitted = True
        logger.info("MLEnsembleModel training complete")

    def predict_proba(self) -> np.ndarray:
        if not self._fitted or self._model is None or self._latest_x is None:
            return np.full(TOTAL_NUMEROS, 1.0 / TOTAL_NUMEROS, dtype=np.float32)
        probas = self._model.predict_proba(self._latest_x)
        result = np.empty(TOTAL_NUMEROS, dtype=np.float32)
        for j, (p, est) in enumerate(zip(probas, self._model.estimators_)):
            if p.shape[1] == 2:
                result[j] = p[0, 1]
            else:
                known_class = est.classes_[0] if hasattr(est, "classes_") else 0
                result[j] = float(known_class)
        return result

    def save(self, path: Path) -> None:
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        joblib.dump(self._model, path / "ml_model.joblib")
        if self._latest_x is not None:
            np.save(path / "ml_latest_x.npy", self._latest_x)

    def load(self, path: Path) -> None:
        path = Path(path)
        self._model = joblib.load(path / "ml_model.joblib")
        x_path = path / "ml_latest_x.npy"
        if x_path.exists():
            self._latest_x = np.load(x_path)
        self._fitted = True