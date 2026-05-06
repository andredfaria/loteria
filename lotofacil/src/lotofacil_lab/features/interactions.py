"""Interaction features between climate and lunar blocks."""

from __future__ import annotations

import numpy as np

# 8 interaction features:
# climate[3] (temp_sorteio) × lunar[0] (phase)
# climate[4] (precip_media) × lunar[3] (illumination)
# climate[3] × lunar[4] (age_norm)
# climate[5] (precip_sorteio) × lunar[5] (is_new)
# climate[5] × lunar[6] (is_full)
# climate[6] (wcode_sorteio) × lunar[0]
# climate[3] × lunar[1] (phase_sin)
# climate[3] × lunar[2] (phase_cos)
N_INTERACTION_FEATURES = 8


def build_interaction_sequences(
    climate_seq: np.ndarray,   # (samples, window, 8)
    lunar_seq: np.ndarray,     # (samples, window, 7)
) -> np.ndarray:
    """Compute element-wise interactions, shape (samples, window, 8)."""
    c = climate_seq
    l = lunar_seq  # noqa: E741
    interactions = np.stack([
        c[..., 3] * l[..., 0],   # temp × phase
        c[..., 4] * l[..., 3],   # precip_media × illumination
        c[..., 3] * l[..., 4],   # temp × age_norm
        c[..., 5] * l[..., 5],   # precip_sorteio × is_new
        c[..., 5] * l[..., 6],   # precip_sorteio × is_full
        c[..., 6] * l[..., 0],   # wcode × phase
        c[..., 3] * l[..., 1],   # temp × phase_sin
        c[..., 3] * l[..., 2],   # temp × phase_cos
    ], axis=-1)
    return interactions.astype(np.float32)
