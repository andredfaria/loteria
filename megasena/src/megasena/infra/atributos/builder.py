from __future__ import annotations

from typing import List, Tuple

import numpy as np

from megasena.dominio.entidades import Sorteio as Draw
from megasena.infra.atributos.base import (
    atraso,
    consecutivos_media,
    faixa_dominante,
    freq_k,
    par_quente_score,
    repeticao_media,
    stats_pares,
    stats_soma,
    std_frequencias,
)
from megasena.infra.atributos.advanced import (
    coocorrencia_score,
    trend_score,
    volatilidade_score,
)

TOTAL = 60
NUMEROS = list(range(1, TOTAL + 1))
MIN_IDX = 20


def _extract(draws: List[Draw], idx: int) -> dict:
    feats: dict = {}

    fk5 = freq_k(draws, idx, 5)
    fk10 = freq_k(draws, idx, 10)
    fk20 = freq_k(draws, idx, 20)
    fk30 = freq_k(draws, idx, 30)
    fk50 = freq_k(draws, idx, 50)

    for n in NUMEROS:
        feats[f"freq_{n}_k5"] = fk5[n]
        feats[f"freq_{n}_k10"] = fk10[n]
        feats[f"freq_{n}_k20"] = fk20[n]
        feats[f"freq_{n}_k30"] = fk30[n]
        feats[f"freq_{n}_k50"] = fk50[n]

    at = atraso(draws, idx, max_atraso=50)
    for n in NUMEROS:
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

    cooc = coocorrencia_score(draws, idx, k=30)
    for n in NUMEROS:
        feats[f"cooc_{n}_k30"] = cooc[n]

    tr = trend_score(draws, idx)
    for n in NUMEROS:
        feats[f"trend_{n}"] = tr[n]

    vol = volatilidade_score(draws, idx)
    for n in NUMEROS:
        feats[f"vol_{n}"] = vol[n]

    feats["faixa_dominante"] = float(faixa_dominante(draws, idx))
    feats["par_quente_score"] = par_quente_score(draws, idx, k=30)

    return feats


def _binary_target(draw: Draw) -> np.ndarray:
    vec = np.zeros(TOTAL, dtype=np.float32)
    for n in draw.dezenas:
        vec[n - 1] = 1.0
    return vec


class FeatureBuilder:
    def __init__(self):
        self.feature_names: List[str] = []
        self.n_features: int = 0

    def build_dataset(self, draws: List[Draw]) -> Tuple[np.ndarray, np.ndarray]:
        n = len(draws)
        if n <= MIN_IDX:
            raise ValueError(f"Need more than {MIN_IDX} draws, got {n}")

        rows_x, rows_y = [], []
        self.feature_names = []
        self.n_features = 0
        for idx in range(MIN_IDX, n):
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