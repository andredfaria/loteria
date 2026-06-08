"""Offline lunar feature calculator using pylunar (no API, no network).
Deterministic and retroactive for any date since 1900+.
Uses São Paulo coordinates (where draws happen) and 21h BRT as draw time.
"""

from __future__ import annotations

import json
import logging
import math
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import List

import numpy as np

from lotofacil.experimentos.config import (
    LATITUDE_SP, LONGITUDE_SP, HORA_SORTEIO, LUA_DIR,
    LUNAR_PERIGEE_KM, LUNAR_APOGEE_KM, LUNAR_CYCLE_DAYS,
    LUNAR_NEW_THRESHOLD, LUNAR_FULL_THRESHOLD,
)

logger = logging.getLogger(__name__)

LUNAR_FEATURE_NAMES = [
    "phase",           # cyclic phase [0, 1) from moon age: 0=nova, 0.5=cheia
    "phase_sin",       # sin(2π × phase) — cyclic encoding
    "phase_cos",       # cos(2π × phase)
    "illumination",    # fraction of disc illuminated [0, 1] (symmetric: ≠ phase)
    "age_norm",        # days since new moon / 29.53 → [0, 1] (== phase)
    "is_new",          # 1 if within ±1.5d of new moon
    "is_full",         # 1 if within ±1.5d of full moon
]
N_LUNAR_FEATURES = len(LUNAR_FEATURE_NAMES)

_DIST_RANGE = LUNAR_APOGEE_KM - LUNAR_PERIGEE_KM

LUA_DIR.mkdir(parents=True, exist_ok=True)


def _cache_path(date_iso: str) -> Path:
    return LUA_DIR / f"{date_iso}.json"


def _load_from_cache(date_iso: str) -> np.ndarray | None:
    path = _cache_path(date_iso)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        feat = data.get("features", {})
        arr = np.array([feat.get(k, 0.0) for k in LUNAR_FEATURE_NAMES], dtype=np.float32)
        return arr
    except Exception:
        return None


def _save_to_cache(date_iso: str, features: dict) -> None:
    path = _cache_path(date_iso)
    path.write_text(json.dumps({"date": date_iso, "features": features}, indent=2))


def _compute_features_raw(date_iso: str, hora: int = HORA_SORTEIO) -> dict:
    """Compute the 7 lunar features for a date via pylunar (no caching).

    The cyclic phase is derived from the moon's *age* (days since new moon),
    NOT from `fractional_phase()` — which returns the illuminated fraction and
    is symmetric around the full moon, so it cannot distinguish waxing from
    waning. `illumination` is kept separately from the elongation.

    Args:
        date_iso: Date in YYYY-MM-DD format.
        hora: Hour of draw in local time (default 21 BRT).

    Returns:
        Dict keyed by LUNAR_FEATURE_NAMES.

    Raises:
        ImportError: if pylunar is unavailable.
        Exception: on date parse / computation failure (caller handles).
    """
    import pylunar

    year, month, day = [int(p) for p in date_iso.split("-")]
    mi = pylunar.MoonInfo(LATITUDE_SP, LONGITUDE_SP)
    mi.update((year, month, day, hora, 0, 0))

    age = mi.age()
    phase = (age / LUNAR_CYCLE_DAYS) % 1.0   # cyclic [0,1): 0=nova, 0.5=cheia
    age_norm = phase

    elongation = mi.elongation()
    illumination = float(np.clip((1 - math.cos(math.radians(elongation))) / 2, 0.0, 1.0))

    dist_from_new = min(phase, 1.0 - phase)
    is_new = 1.0 if dist_from_new < LUNAR_NEW_THRESHOLD else 0.0
    dist_from_full = abs(phase - 0.5)
    is_full = 1.0 if dist_from_full < LUNAR_FULL_THRESHOLD else 0.0

    return {
        "phase": phase,
        "phase_sin": math.sin(2 * math.pi * phase),
        "phase_cos": math.cos(2 * math.pi * phase),
        "illumination": illumination,
        "age_norm": age_norm,
        "is_new": is_new,
        "is_full": is_full,
    }


@lru_cache(maxsize=4096)
def compute_lunar_features(date_iso: str, hora: int = HORA_SORTEIO) -> np.ndarray:
    """Compute 7 lunar features for a given date and hour (BRT).

    Checks `dados/lua/<date_iso>.json` cache first.
    If missing, computes via pylunar and saves to cache.

    Args:
        date_iso: Date in YYYY-MM-DD format.
        hora: Hour of draw in local time (default 21 BRT).

    Returns:
        float32 array of shape (7,). Returns zeros on parse error.
    """
    # Try loading from disk cache
    cached = _load_from_cache(date_iso)
    if cached is not None:
        return cached

    try:
        features = _compute_features_raw(date_iso, hora)
    except ImportError:
        logger.error("pylunar not installed. Run: pip install pylunar")
        return np.zeros(N_LUNAR_FEATURES, dtype=np.float32)
    except Exception as exc:
        logger.warning("Lunar computation failed for %s: %s", date_iso, exc)
        return np.zeros(N_LUNAR_FEATURES, dtype=np.float32)

    arr = np.array([features[k] for k in LUNAR_FEATURE_NAMES], dtype=np.float32)
    _save_to_cache(date_iso, features)
    return arr


def recompute_lunar_cache(date_iso: str, hora: int = HORA_SORTEIO) -> np.ndarray:
    """Recompute features ignoring the cache and overwrite the JSON on disk.

    Use to repair caches written by an older, buggy version of the
    computation. Also clears the in-process lru_cache for this date.

    Returns:
        float32 array of shape (7,). Returns zeros on failure.
    """
    try:
        features = _compute_features_raw(date_iso, hora)
    except ImportError:
        logger.error("pylunar not installed. Run: pip install pylunar")
        return np.zeros(N_LUNAR_FEATURES, dtype=np.float32)
    except Exception as exc:
        logger.warning("Lunar recompute failed for %s: %s", date_iso, exc)
        return np.zeros(N_LUNAR_FEATURES, dtype=np.float32)

    _save_to_cache(date_iso, features)
    compute_lunar_features.cache_clear()
    return np.array([features[k] for k in LUNAR_FEATURE_NAMES], dtype=np.float32)


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
