"""Offline lunar feature calculator using pylunar (no API, no network).

Deterministic and retroactive for any date since 1900+.
Uses São Paulo coordinates (where draws happen) and 20h BRT as draw time.
"""

from __future__ import annotations

import logging
import math
from datetime import datetime
from functools import lru_cache
from typing import List

import numpy as np

from lotofacil_lab.config import (
    LATITUDE_SP, LONGITUDE_SP, HORA_SORTEIO,
    LUNAR_PERIGEE_KM, LUNAR_APOGEE_KM, LUNAR_CYCLE_DAYS,
    LUNAR_NEW_THRESHOLD, LUNAR_FULL_THRESHOLD,
)

logger = logging.getLogger(__name__)

LUNAR_FEATURE_NAMES = [
    "phase",           # fractional phase [0, 1): 0=nova, 0.5=cheia
    "phase_sin",       # sin(2π × phase) — cyclic encoding
    "phase_cos",       # cos(2π × phase)
    "illumination",    # fraction of disc illuminated [0, 1]
    "age_norm",        # days since new moon / 29.53 → [0, 1]
    "is_new",          # 1 if within ±1.5d of new moon
    "is_full",         # 1 if within ±1.5d of full moon
]
N_LUNAR_FEATURES = len(LUNAR_FEATURE_NAMES)

_DIST_RANGE = LUNAR_APOGEE_KM - LUNAR_PERIGEE_KM


@lru_cache(maxsize=4096)
def compute_lunar_features(date_iso: str, hora: int = HORA_SORTEIO) -> np.ndarray:
    """Compute 7 lunar features for a given date and hour (BRT).

    Args:
        date_iso: Date in YYYY-MM-DD format.
        hora: Hour of draw in local time (default 20 BRT).

    Returns:
        float32 array of shape (7,). Returns zeros on parse error.
    """
    try:
        import pylunar
    except ImportError:
        logger.error("pylunar not installed. Run: pip install pylunar")
        return np.zeros(N_LUNAR_FEATURES, dtype=np.float32)

    try:
        year, month, day = [int(p) for p in date_iso.split("-")]
        mi = pylunar.MoonInfo(LATITUDE_SP, LONGITUDE_SP)
        mi.update((year, month, day, hora, 0, 0))

        phase = mi.fractional_phase()      # [0, 1)
        age = mi.age()                     # days since new moon

        # Illumination from elongation angle (0=new, 180=full)
        elongation = mi.elongation()
        illumination = (1 - math.cos(math.radians(elongation))) / 2
        illumination = float(np.clip(illumination, 0.0, 1.0))

        age_norm = age / LUNAR_CYCLE_DAYS

        # is_new: close to 0.0 or 1.0 in fractional_phase
        dist_from_new = min(phase, 1.0 - phase)
        is_new = 1.0 if dist_from_new < LUNAR_NEW_THRESHOLD else 0.0

        # is_full: close to 0.5 in fractional_phase
        dist_from_full = abs(phase - 0.5)
        is_full = 1.0 if dist_from_full < LUNAR_FULL_THRESHOLD else 0.0

        return np.array([
            phase,
            math.sin(2 * math.pi * phase),
            math.cos(2 * math.pi * phase),
            illumination,
            age_norm,
            is_new,
            is_full,
        ], dtype=np.float32)

    except Exception as exc:
        logger.warning("Lunar computation failed for %s: %s", date_iso, exc)
        return np.zeros(N_LUNAR_FEATURES, dtype=np.float32)


def _parse_iso(date_str: str) -> str:
    """Convert DD/MM/YYYY → YYYY-MM-DD. Returns empty string on failure."""
    try:
        if "/" in date_str:
            return datetime.strptime(date_str.strip(), "%d/%m/%Y").strftime("%Y-%m-%d")
        return date_str.strip()
    except (ValueError, AttributeError):
        return ""


def get_lunar_matrix(draws) -> np.ndarray:
    """Compute lunar features aligned with a list of Draw objects.

    Args:
        draws: list of Draw objects (must have .data in DD/MM/YYYY or YYYY-MM-DD).

    Returns:
        Array of shape (n, 7), float32.
    """
    n = len(draws)
    out = np.zeros((n, N_LUNAR_FEATURES), dtype=np.float32)
    errors = 0

    for i, draw in enumerate(draws):
        iso = _parse_iso(draw.data)
        if not iso:
            errors += 1
            continue
        out[i] = compute_lunar_features(iso)

    if errors:
        logger.warning("%d draws had unparseable dates; lunar features set to zero", errors)

    return out


def get_lunar_features_dict(date_iso: str) -> dict:
    """Return lunar features as a labelled dict for inspection."""
    feats = compute_lunar_features(date_iso)
    return dict(zip(LUNAR_FEATURE_NAMES, feats.tolist()))
