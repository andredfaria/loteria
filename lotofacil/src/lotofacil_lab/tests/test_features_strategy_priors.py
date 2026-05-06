"""Tests for strategy_priors feature module."""

import numpy as np
import pytest

from lotofacil_lab.features.strategy_priors import (
    build_strategy_priors_matrix,
    build_strategy_priors_sequences,
    N_STRATEGY_FEATURES,
)


def test_matrix_shape(sample_draws):
    mat = build_strategy_priors_matrix(sample_draws)
    assert mat.shape == (len(sample_draws), N_STRATEGY_FEATURES)


def test_matrix_range(sample_draws):
    mat = build_strategy_priors_matrix(sample_draws)
    assert np.all(mat >= 0.0) and np.all(mat <= 1.0)


def test_sequences_shape(sample_draws):
    window = 10
    seq = build_strategy_priors_sequences(sample_draws, window)
    expected = len(sample_draws) - window
    assert seq.shape == (expected, window, N_STRATEGY_FEATURES)


def test_soma_score_valid(sample_draws):
    """Soma score (col 0) should be in [0, 1]."""
    mat = build_strategy_priors_matrix(sample_draws)
    assert np.all(mat[:, 0] >= 0.0) and np.all(mat[:, 0] <= 1.0)


def test_ciclo_score_valid(sample_draws):
    """Ciclo score (col 7) represents fraction of 25 numbers seen in last 4 draws."""
    mat = build_strategy_priors_matrix(sample_draws)
    assert np.all(mat[:, 7] >= 0.0) and np.all(mat[:, 7] <= 1.0)
