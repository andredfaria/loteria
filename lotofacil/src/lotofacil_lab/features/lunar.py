"""Lunar features wrapper for the lab feature builder."""

from __future__ import annotations

import numpy as np

from lotofacil_lab.data.lunar_loader import get_lunar_matrix, N_LUNAR_FEATURES

N_LUNAR_FEATURES = N_LUNAR_FEATURES  # re-export


def build_lunar_sequences(draws, window: int) -> np.ndarray:
    """Shape (n - window, window, 7).

    Each timestep in the window carries the lunar features from the
    corresponding historical draw.
    """
    flat = get_lunar_matrix(draws)  # (n, 7)
    seqs = []
    for i in range(window, len(draws)):
        seqs.append(flat[i - window:i])
    return np.array(seqs, dtype=np.float32)
