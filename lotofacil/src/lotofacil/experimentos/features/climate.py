"""Climate features wrapper for the lab feature builder."""

from __future__ import annotations

import numpy as np

from lotofacil.experimentos.data.climate_loader import get_climate_matrix, N_CLIMATE_FEATURES

N_CLIMATE_FEATURES = N_CLIMATE_FEATURES  # re-export


def build_climate_sequences(draws, window: int) -> np.ndarray:
    """Shape (n - window, window, 8).

    Returns climate features expanded as sequences — each timestep in the
    window carries the climate from the corresponding historical draw.
    Draws without climate data get zero vectors.
    """
    flat = get_climate_matrix(draws)  # (n, 8)
    seqs = []
    for i in range(window, len(draws)):
        seqs.append(flat[i - window:i])
    return np.array(seqs, dtype=np.float32)
