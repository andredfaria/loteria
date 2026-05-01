"""Feature builder: assembles per-concurso feature vectors with no data leakage."""

from __future__ import annotations

from typing import List, Tuple

import numpy as np

from lotofacil_ml.data.loader import Draw
from lotofacil_ml.features.base import (
    freq_k,
    atraso,
    stats_soma,
    stats_pares,
    repeticao_media,
    consecutivos_media,
    std_frequencias,
    ratio_moldura_miolo,
)
from lotofacil_ml.features.advanced import (
    coocorrencia_score,
    trend_score,
    volatilidade_score,
    faixa_dominante,
    par_quente_score,
)

_NUMBERS = list(range(1, 26))
_MIN_IDX = 20  # need at least 20 draws of history


def _extract(draws: List[Draw], idx: int) -> dict:
    """Extract all features for the draw at idx, using only draws[:idx]."""
    feats: dict = {}

    fk5 = freq_k(draws, idx, 5)
    fk10 = freq_k(draws, idx, 10)
    fk20 = freq_k(draws, idx, 20)

    for n in _NUMBERS:
        feats[f"freq_{n}_k5"] = fk5[n]
        feats[f"freq_{n}_k10"] = fk10[n]
        feats[f"freq_{n}_k20"] = fk20[n]

    at = atraso(draws, idx)
    for n in _NUMBERS:
        feats[f"atraso_{n}"] = float(at[n])

    for k, sfx in [(5, "k5"), (10, "k10"), (20, "k20")]:
        s = stats_soma(draws, idx, k)
        feats[f"soma_mean_{sfx}"] = s["mean"]
        feats[f"soma_median_{sfx}"] = s["median"]
        feats[f"soma_std_{sfx}"] = s["std"]

    for k, sfx in [(5, "k5"), (10, "k10"), (20, "k20")]:
        mp, mi = stats_pares(draws, idx, k)
        feats[f"pares_mean_{sfx}"] = mp
        feats[f"impares_mean_{sfx}"] = mi

    for k, sfx in [(5, "k5"), (10, "k10"), (20, "k20")]:
        feats[f"repeticao_mean_{sfx}"] = repeticao_media(draws, idx, k)
        feats[f"consecutivos_mean_{sfx}"] = consecutivos_media(draws, idx, k)

    feats["std_frequencias"] = std_frequencias(fk20)
    feats["ratio_moldura_miolo"] = ratio_moldura_miolo(draws, idx)

    cooc = coocorrencia_score(draws, idx, k=30)
    for n in _NUMBERS:
        feats[f"cooc_{n}_k30"] = cooc[n]

    tr = trend_score(draws, idx)
    for n in _NUMBERS:
        feats[f"trend_{n}"] = tr[n]

    vol = volatilidade_score(draws, idx)
    for n in _NUMBERS:
        feats[f"vol_{n}"] = vol[n]

    feats["faixa_dominante"] = float(faixa_dominante(draws, idx))
    feats["par_quente_score"] = par_quente_score(draws, idx, k=30)

    return feats


def _binary_target(draw: Draw) -> np.ndarray:
    """Binary vector of shape (25,): 1 if number appeared."""
    vec = np.zeros(25, dtype=np.float32)
    for n in draw.dezenas:
        vec[n - 1] = 1.0
    return vec


class FeatureBuilder:
    """Builds feature matrices for training and inference."""

    def __init__(self):
        self.feature_names: List[str] = []
        self.n_features: int = 0

    def build_dataset(self, draws: List[Draw]) -> Tuple[np.ndarray, np.ndarray]:
        """
        Build X (n_samples, n_features) and y (n_samples, 25).

        For sample i:
          - X[i] = features extracted from draws[:_MIN_IDX + i]  (idx = _MIN_IDX + i)
          - y[i] = binary target for draws[_MIN_IDX + i]

        Guarantees no data leakage: feature at row i uses only
        draws up to index (_MIN_IDX + i - 1).
        """
        n = len(draws)
        if n <= _MIN_IDX:
            raise ValueError(f"Need more than {_MIN_IDX} draws, got {n}")

        rows_x, rows_y = [], []
        self.feature_names = []  # reset on every call
        self.n_features = 0
        for idx in range(_MIN_IDX, n):
            feats = _extract(draws, idx)
            if not self.feature_names:
                self.feature_names = list(feats.keys())
                self.n_features = len(self.feature_names)
            rows_x.append([feats[k] for k in self.feature_names])
            rows_y.append(_binary_target(draws[idx]))

        X = np.array(rows_x, dtype=np.float32)
        y = np.array(rows_y, dtype=np.float32)
        return X, y

    def build_inference(self, draws: List[Draw]) -> np.ndarray:
        """
        Feature vector for the NEXT (unseen) draw, shape (1, n_features).
        Uses all available draws as history.
        """
        idx = len(draws)
        feats = _extract(draws, idx)
        if not self.feature_names:
            self.feature_names = list(feats.keys())
            self.n_features = len(self.feature_names)
        x = np.array([[feats[k] for k in self.feature_names]], dtype=np.float32)
        return x
