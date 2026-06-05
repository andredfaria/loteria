"""Modelo A — LightGBM que prevê quais 15 dezenas saem no próximo concurso.

Treina sobre a matriz long (concurso × número) de dataset_ml.to_training_matrix.
Avaliação honesta: acertos@15 vs baseline aleatório (~9 esperados, hipergeométrico).
"""

from __future__ import annotations

from typing import Tuple

import numpy as np
import pandas as pd

from lotofacil.experimentos.data.dataset_ml import (
    CLIMA_COLS, LUNAR_FEATURE_NAMES, TEMPORAL_COLS,
)

FEATURE_COLS = (
    ["numero", "freq_10", "freq_30", "freq_100", "freq_all",
     "days_since_last", "saiu_no_anterior"]
    + list(CLIMA_COLS) + list(LUNAR_FEATURE_NAMES) + list(TEMPORAL_COLS)
)
TARGET = "saiu_no_proximo"
BASELINE_ALEATORIO = 15 * 15 / 25  # = 9.0 (média hipergeométrica)


def temporal_split(long_df: pd.DataFrame, frac: float = 0.8) -> Tuple[pd.DataFrame, pd.DataFrame]:
    concursos = sorted(long_df["concurso"].unique())
    cut_idx = int(len(concursos) * frac)
    cut = concursos[cut_idx]
    train = long_df[long_df["concurso"] < cut].copy()
    test = long_df[long_df["concurso"] >= cut].copy()
    return train, test


def train_model(train_df: pd.DataFrame):
    import lightgbm as lgb
    X = train_df[FEATURE_COLS]
    y = train_df[TARGET]
    model = lgb.LGBMClassifier(
        n_estimators=200, learning_rate=0.05, num_leaves=31,
        random_state=42, n_jobs=-1, verbose=-1,
    )
    model.fit(X, y)
    return model


def evaluate(model, test_df: pd.DataFrame) -> dict:
    from sklearn.metrics import log_loss, roc_auc_score

    proba = model.predict_proba(test_df[FEATURE_COLS])[:, 1]
    test_df = test_df.assign(_proba=proba)

    hits = []
    for _, grp in test_df.groupby("concurso"):
        top15 = set(grp.sort_values("_proba", ascending=False).head(15)["numero"])
        actual = set(grp[grp[TARGET] == 1]["numero"])
        hits.append(len(top15 & actual))

    y_true = test_df[TARGET].to_numpy()
    metrics = {
        "acertos_medio": float(np.mean(hits)),
        "acertos_std": float(np.std(hits)),
        "baseline_aleatorio": BASELINE_ALEATORIO,
        "n_concursos_teste": len(hits),
        "auc": float(roc_auc_score(y_true, proba)) if len(set(y_true)) > 1 else float("nan"),
        "logloss": float(log_loss(y_true, proba, labels=[0, 1])),
    }
    return metrics
