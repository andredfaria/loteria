"""Temporal features: cyclic encoding of day-of-week and month."""

from __future__ import annotations

import math
from datetime import datetime

import numpy as np

N_TEMPORAL_FEATURES = 4  # sin_dow, cos_dow, sin_month, cos_month


def _parse_date(date_str: str) -> datetime:
    try:
        if "/" in date_str:
            return datetime.strptime(date_str.strip(), "%d/%m/%Y")
        return datetime.strptime(date_str.strip(), "%Y-%m-%d")
    except (ValueError, AttributeError):
        return datetime(2000, 1, 1)


def build_temporal_matrix(draws) -> np.ndarray:
    """Shape (n, 4): sin_dow, cos_dow, sin_month, cos_month."""
    n = len(draws)
    out = np.zeros((n, N_TEMPORAL_FEATURES), dtype=np.float32)
    for i, draw in enumerate(draws):
        dt = _parse_date(draw.data)
        dow = dt.weekday()      # 0=Monday … 6=Sunday
        month = dt.month - 1   # 0-based
        out[i, 0] = math.sin(2 * math.pi * dow / 7)
        out[i, 1] = math.cos(2 * math.pi * dow / 7)
        out[i, 2] = math.sin(2 * math.pi * month / 12)
        out[i, 3] = math.cos(2 * math.pi * month / 12)
    return out


def build_temporal_sequences(draws, window: int) -> np.ndarray:
    """Shape (n - window, window, 4)."""
    flat = build_temporal_matrix(draws)
    seqs = []
    for i in range(window, len(draws)):
        seqs.append(flat[i - window:i])
    return np.array(seqs, dtype=np.float32)
