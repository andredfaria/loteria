"""Wrapper over src/data/climate_loader.py for the lab pipeline.

Thin adapter that:
- delegates to the existing climate_loader (load_all_climate, normalize_climate)
- returns shape (n, 8) array aligned with a list of Draw objects
- returns zeros for draws without climate data (graceful degradation)
"""

from __future__ import annotations

import logging
from typing import List

import numpy as np

from lotofacil_lab.config import SRC_DIR  # noqa: F401 — sets sys.path

logger = logging.getLogger(__name__)

# 8 feature names (same order as normalize_climate output)
CLIMATE_FEATURE_NAMES = [
    "temp_min",
    "temp_max",
    "temp_media",
    "temp_sorteio",
    "precip_media",
    "precip_sorteio",
    "wcode_sorteio",
    "wcode_dominant",
]
N_CLIMATE_FEATURES = len(CLIMATE_FEATURE_NAMES)


def get_climate_matrix(draws) -> np.ndarray:
    """Return climate features aligned with draws.

    Args:
        draws: list of Draw objects (must have .concurso and .data).

    Returns:
        Array of shape (n, 8), float32. Missing → zeros (logged as warning).
    """
    from data.climate_loader import load_all_climate, normalize_climate  # src/data/

    climate_map = load_all_climate()
    n = len(draws)
    out = np.zeros((n, N_CLIMATE_FEATURES), dtype=np.float32)
    missing = 0

    for i, draw in enumerate(draws):
        resumo = climate_map.get(draw.concurso)
        if resumo:
            out[i] = normalize_climate(resumo)
        else:
            missing += 1

    if missing:
        coverage = (n - missing) / n * 100
        logger.info("Climate coverage: %.1f%% (%d/%d draws)", coverage, n - missing, n)

    return out


def get_coverage_pct(draws) -> float:
    """Return fraction of draws that have climate data."""
    from data.climate_loader import load_all_climate
    climate_map = load_all_climate()
    if not draws:
        return 0.0
    covered = sum(1 for d in draws if d.concurso in climate_map)
    return covered / len(draws) * 100
