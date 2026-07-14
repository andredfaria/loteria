from __future__ import annotations

from typing import List, Tuple

import numpy as np

from quina.dominio.entidades import Sorteio as Draw
from quina.infra.atributos.base import (
    freq_k,
    atraso,
    stats_soma,
    stats_pares,
    repeticao_media,
    consecutivos_media,
    std_frequencias,
)
from quina.infra.atributos.advanced import (
    faixa_dominante,
    par_quente_score,
)

_NUMBERS = list(range(1, 81))
_MIN_IDX = 50


def _extract(draws: List[Draw], idx: int) -> dict:
    feats: dict = {}

    fk10 = freq_k(draws, idx, 10)
    fk30 = freq_k(draws, idx, 30)
    fk50 = freq_k(draws, idx, 50)

    for n in _NUMBERS:
        feats[f"freq_{n}_k10"] = fk10[n]
        feats[f"freq_{n}_k30"] = fk30[n]
        feats[f"freq_{n}_k50"] = fk50[n]

    at = atraso(draws, idx)
    for n in _NUMBERS:
        feats[f"atraso_{n}"] = float(at[n])

    for k, sfx in [(10, "k10"), (30, "k30"), (50, "k50")]:
        s = stats_soma(draws, idx, k)
        feats[f"soma_mean_{sfx}"] = s["mean"]
        feats[f"soma_median_{sfx}"] = s["median"]
        feats[f"soma_std_{sfx}"] = s["std"]

    for k, sfx in [(10, "k10"), (30, "k30"), (50, "k50")]:
        mp, mi = stats_pares(draws, idx, k)
        feats[f"pares_mean_{sfx}"] = mp
        feats[f"impares_mean_{sfx}"] = mi

    for k, sfx in [(10, "k10"), (30, "k30"), (50, "k50")]:
        feats[f"repeticao_mean_{sfx}"] = repeticao_media(draws, idx, k)
        feats[f"consecutivos_mean_{sfx}"] = consecutivos_media(draws, idx, k)

    feats["std_frequencias"] = std_frequencias(fk30)

    feats["faixa_dominante"] = float(faixa_dominante(draws, idx))
    feats["par_quente_score"] = par_quente_score(draws, idx, k=50)

    return feats


def _binary_target(draw: Draw) -> np.ndarray:
    vec = np.zeros(80, dtype=np.float32)
    for n in draw.dezenas:
        vec[n - 1] = 1.0
    return vec


class FeatureBuilder:
    def __init__(self):
        self.feature_names: List[str] = []
        self.n_features: int = 0

    def build_dataset(self, draws: List[Draw]) -> Tuple[np.ndarray, np.ndarray]:
        n = len(draws)
        if n <= _MIN_IDX:
            raise ValueError(f"Need more than {_MIN_IDX} draws, got {n}")

        rows_x, rows_y = [], []
        self.feature_names = []
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
        idx = len(draws)
        feats = _extract(draws, idx)
        if not self.feature_names:
            self.feature_names = list(feats.keys())
            self.n_features = len(self.feature_names)
        x = np.array([[feats[k] for k in self.feature_names]], dtype=np.float32)
        return x