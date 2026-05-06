"""Permutation importance at feature-block level.

For each block, shuffle its values across the time dimension and measure
the drop in mean hits vs the unperturbed prediction. Larger drop = higher
importance.
"""

from __future__ import annotations

import logging
from copy import deepcopy
from typing import Callable, Dict, List

import numpy as np

from lotofacil_lab.evaluation.metrics import mean_hits

logger = logging.getLogger(__name__)


def permutation_importance_blocks(
    X: np.ndarray,           # (samples, window, n_features)
    y: np.ndarray,           # (samples, 25) binary
    model,                   # fitted model with a predict_from_X method or keras model
    block_slices: Dict[str, slice],
    n_repeats: int = 5,
    target_numbers: int = 15,
    seed: int = 42,
) -> Dict[str, float]:
    """Estimate block-level importances by shuffling feature columns.

    Args:
        X: Feature tensor.
        y: Binary target matrix.
        model: A keras-compatible model exposing .predict(X).
        block_slices: Maps block name → slice in X's last axis.
        n_repeats: Number of shuffles per block (averaged).
        target_numbers: How many top dezenas to select from probabilities.
        seed: RNG seed.

    Returns:
        Dict mapping block name → mean_hits drop (positive = more important).
    """
    rng = np.random.default_rng(seed)

    # Baseline hits using unperturbed X
    proba_base = model.predict(X, verbose=0)  # (samples, 25)
    hits_base = _top_hits(proba_base, y, target_numbers)
    baseline = mean_hits([{"hits": h} for h in hits_base])
    logger.info("Permutation baseline mean_hits=%.4f", baseline)

    importances: Dict[str, float] = {}

    for block_name, sl in block_slices.items():
        drops = []
        for _ in range(n_repeats):
            X_perturbed = X.copy()
            # Shuffle samples independently for each column in the block
            for col in range(sl.start, sl.stop):
                perm = rng.permutation(X.shape[0])
                X_perturbed[:, :, col] = X[perm, :, col]

            proba = model.predict(X_perturbed, verbose=0)
            hits = _top_hits(proba, y, target_numbers)
            drops.append(baseline - mean_hits([{"hits": h} for h in hits]))

        importance = float(np.mean(drops))
        importances[block_name] = round(importance, 4)
        logger.info("Block '%s': importance=%.4f", block_name, importance)

    return importances


def _top_hits(proba: np.ndarray, y: np.ndarray, target_numbers: int) -> List[int]:
    """Given probability matrix (n, 25), count hits against y for top-N selection."""
    hits = []
    for i in range(len(proba)):
        top = set(np.argsort(proba[i])[::-1][:target_numbers])
        actual = set(np.where(y[i] == 1)[0])
        hits.append(len(top & actual))
    return hits
