"""Tests for base feature module."""

import numpy as np
import pytest

from lotofacil_lab.features.base import (
    binary_matrix,
    sliding_frequency,
    days_since_last,
    build_base_matrix,
    build_base_sequences,
    N_BASE_FEATURES,
)


def test_binary_matrix_shape(sample_draws):
    mat = binary_matrix(sample_draws)
    assert mat.shape == (len(sample_draws), 25)


def test_binary_matrix_values(sample_draws):
    mat = binary_matrix(sample_draws)
    assert np.all((mat == 0) | (mat == 1))
    assert mat.sum(axis=1).tolist() == [15.0] * len(sample_draws)


def test_sliding_frequency_lagged(sample_draws):
    binary = binary_matrix(sample_draws)
    freq = sliding_frequency(binary, window=5)
    # Row 0 must be zeros (no prior draws)
    np.testing.assert_array_equal(freq[0], np.zeros(25))


def test_days_since_last_clipped(sample_draws):
    binary = binary_matrix(sample_draws)
    atraso = days_since_last(binary, norm=50.0)
    assert np.all(atraso >= 0) and np.all(atraso <= 1)


def test_build_base_matrix_shape(sample_draws):
    mat = build_base_matrix(sample_draws)
    assert mat.shape == (len(sample_draws), N_BASE_FEATURES)


def test_build_base_sequences_shape(sample_draws):
    window = 10
    seq = build_base_sequences(sample_draws, window)
    expected_samples = len(sample_draws) - window
    assert seq.shape == (expected_samples, window, N_BASE_FEATURES)


def test_build_base_sequences_dtype(sample_draws):
    seq = build_base_sequences(sample_draws, window=5)
    assert seq.dtype == np.float32


def test_not_enough_draws_for_window(minimal_draws):
    window = 20  # more than 10 draws
    seq = build_base_sequences(minimal_draws, window)
    assert seq.shape[0] == 0  # no valid samples
