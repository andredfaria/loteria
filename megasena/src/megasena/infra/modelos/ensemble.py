from __future__ import annotations

import logging
import warnings
from pathlib import Path
from typing import List

import numpy as np

from megasena.dominio.entidades import Sorteio as Draw
from megasena.infra.config import MODELOS_DIR
from megasena.infra.modelos.base_model import NUMEROS_POR_SORTEIO
from megasena.infra.modelos.frequency_ensemble import FrequencyEnsembleModel
from megasena.infra.modelos.ml_model import MLEnsembleModel
from megasena.infra.modelos.probabilistic import ProbabilisticModel

logger = logging.getLogger(__name__)

TOTAL_NUMEROS = 60

_DEFAULT_WEIGHTS = {"frequency": 0.20, "ml": 0.50, "probabilistic": 0.30}


def _para_percentil(v: np.ndarray) -> np.ndarray:
    """Mapeia um score para [0, 1] preservando apenas a ORDEM.

    Existe para que os pesos do ensemble signifiquem o que prometem. Os
    submodelos devolvem scores em escalas incompatíveis: `frequency` e
    `probabilistic` são min-max normalizados (amplitude ~1,0) enquanto `ml`
    devolve probabilidades calibradas concentradas em torno de
    NUMEROS_POR_SORTEIO/TOTAL_NUMEROS (amplitude ~0,15). Somando direto, o que
    decide o ranking é a amplitude ponderada, não o peso: com os pesos padrão,
    `ml` pesava nominalmente 0,50 mas influenciava ~13% do resultado.

    O rank percentil é invariante a escala, então dobrar um peso passa a
    dobrar a influência daquele submodelo, como qualquer leitor esperaria.
    """
    n = v.shape[0]
    if n <= 1:
        return np.zeros_like(v, dtype=np.float32)
    ordem = np.argsort(np.argsort(v, kind="stable"), kind="stable")
    return (ordem / (n - 1)).astype(np.float32)


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
        self.frequency.fit(draws)
        self.ml.fit(draws)
        self.probabilistic.fit(draws)
        self._fitted = True

    def score(self) -> np.ndarray:
        """Score de ordenação combinado em [0, 1] para cada número.

        NÃO é uma probabilidade estatística — é a combinação ponderada dos
        scores (também min-max normalizados) dos submodelos. Serve apenas
        para ranquear números entre si; a chance real de qualquer número sair
        é sempre NUMEROS_POR_SORTEIO / TOTAL_NUMEROS.
        """
        if not self._fitted:
            return np.full(TOTAL_NUMEROS, 1.0 / TOTAL_NUMEROS, dtype=np.float32)
        # Cada submodelo passa por rank percentil antes de entrar na soma:
        # sem isso, o peso nominal não corresponde à influência real (ver
        # docstring de _para_percentil).
        p_freq = _para_percentil(self.frequency.score())
        p_ml = _para_percentil(self.ml.score())
        p_prob = _para_percentil(self.probabilistic.score())
        combined = (
            self.weights.get("frequency", 0.2) * p_freq
            + self.weights.get("ml", 0.5) * p_ml
            + self.weights.get("probabilistic", 0.3) * p_prob
        )
        return combined.astype(np.float32)

    def predict_proba(self) -> np.ndarray:
        """Alias legado de `score()`, mantido para compatibilidade. Prefira `score()`."""
        warnings.warn(
            "predict_proba() está depreciado; use score(). O valor retornado é "
            "um score de ordenação em [0,1], não uma probabilidade estatística.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.score()

    def select_top_6(self) -> List[int]:
        p = self.score()
        indices = np.argsort(p)[::-1][:NUMEROS_POR_SORTEIO]
        return sorted(int(i + 1) for i in indices)

    def select_top_n(self, n: int = 12) -> List[int]:
        p = self.score()
        indices = np.argsort(p)[::-1][:n]
        return [int(i + 1) for i in indices]

    def score_dict(self) -> dict[int, float]:
        p = self.score()
        return {i + 1: float(p[i]) for i in range(TOTAL_NUMEROS)}

    def predict_proba_dict(self) -> dict[int, float]:
        """Alias legado de `score_dict()`, mantido para compatibilidade. Prefira `score_dict()`."""
        warnings.warn(
            "predict_proba_dict() está depreciado; use score_dict(). O valor "
            "retornado é um score de ordenação em [0,1], não uma probabilidade.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.score_dict()

    def save(self) -> None:
        self.frequency.save(self.models_dir)
        self.ml.save(self.models_dir)
        self.probabilistic.save(self.models_dir)

    def load(self) -> None:
        loaded = 0
        for model, attr in [
            (self.frequency, "frequency"),
            (self.ml, "ml"),
            (self.probabilistic, "probabilistic"),
        ]:
            try:
                model.load(self.models_dir)
                loaded += 1
            except Exception as exc:
                logger.warning("%s load failed: %s", attr, exc)
        if loaded == 0:
            logger.error("EnsemblePredictor: all sub-model loads failed")
        self._fitted = loaded > 0