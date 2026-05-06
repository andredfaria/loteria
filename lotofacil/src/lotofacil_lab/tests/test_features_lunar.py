"""Tests for lunar feature sequences."""

import numpy as np
import pytest

from lotofacil_lab.features.lunar import build_lunar_sequences, N_LUNAR_FEATURES


def test_build_lunar_sequences_shape(sample_draws):
    window = 5
    seq = build_lunar_sequences(sample_draws, window)
    expected = len(sample_draws) - window
    assert seq.shape == (expected, window, N_LUNAR_FEATURES)


def test_build_lunar_sequences_dtype(sample_draws):
    seq = build_lunar_sequences(sample_draws, window=5)
    assert seq.dtype == np.float32


def test_build_lunar_sequences_range(sample_draws):
    """Phase values [col 0] must be in [0, 1)."""
    seq = build_lunar_sequences(sample_draws, window=5)
    phase = seq[:, :, 0]
    assert np.all(phase >= 0.0) and np.all(phase < 1.0)
