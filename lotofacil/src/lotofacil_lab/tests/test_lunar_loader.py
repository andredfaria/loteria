"""Tests for lunar_loader."""

import math

import numpy as np
import pytest

from lotofacil_lab.data.lunar_loader import (
    compute_lunar_features,
    get_lunar_matrix,
    get_lunar_features_dict,
    LUNAR_FEATURE_NAMES,
    N_LUNAR_FEATURES,
)


def test_feature_count():
    assert len(LUNAR_FEATURE_NAMES) == N_LUNAR_FEATURES == 7


def test_compute_shape():
    feat = compute_lunar_features("2025-12-04")
    assert feat.shape == (7,)
    assert feat.dtype == np.float32


def test_phase_range():
    feat = compute_lunar_features("2026-01-15")
    phase = float(feat[0])
    assert 0.0 <= phase < 1.0


def test_illumination_range():
    feat = compute_lunar_features("2026-01-15")
    illumination = float(feat[3])
    assert 0.0 <= illumination <= 1.0


def test_age_norm_range():
    feat = compute_lunar_features("2026-01-15")
    age_norm = float(feat[4])
    assert 0.0 <= age_norm <= 1.0


def test_sin_cos_unit_circle():
    feat = compute_lunar_features("2026-01-15")
    phase_sin, phase_cos = float(feat[1]), float(feat[2])
    radius = math.sqrt(phase_sin ** 2 + phase_cos ** 2)
    assert abs(radius - 1.0) < 0.01, f"sin²+cos² should ≈ 1, got {radius}"


def test_is_new_is_full_binary():
    feat = compute_lunar_features("2026-01-15")
    assert feat[5] in (0.0, 1.0)
    assert feat[6] in (0.0, 1.0)


def test_historical_date_works():
    """pylunar should handle dates as far back as 2003 (first Lotofácil draw)."""
    feat = compute_lunar_features("2003-09-29")
    assert feat.shape == (7,)
    assert not np.all(feat == 0.0), "Historical date returned all zeros"


def test_invalid_date_returns_zeros():
    feat = compute_lunar_features("not-a-date")
    assert np.all(feat == 0.0)


def test_get_lunar_matrix(sample_draws):
    mat = get_lunar_matrix(sample_draws)
    assert mat.shape == (len(sample_draws), N_LUNAR_FEATURES)
    assert mat.dtype == np.float32


def test_get_lunar_features_dict():
    d = get_lunar_features_dict("2025-06-11")
    assert set(d.keys()) == set(LUNAR_FEATURE_NAMES)


def test_caching():
    """Two calls with same date should return identical arrays (LRU cache)."""
    a = compute_lunar_features("2025-12-04")
    b = compute_lunar_features("2025-12-04")
    np.testing.assert_array_equal(a, b)
