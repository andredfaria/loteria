"""Tests for LotofacilPreprocessor."""

import numpy as np
import pytest

from lotofacil_ml.data.preprocessor import LotofacilPreprocessor
from lotofacil_ml.config import TOTAL_NUMBERS, LSTM_WINDOW_SIZE


# ── Fixtures ───────────────────────────────────────────────────────────────────

def _make_draws(n: int = 200):
    """Generate n synthetic draws with deterministic but varied dezenas."""
    import random
    rng = random.Random(42)
    draws = []
    for i in range(n):
        dezenas = sorted(rng.sample(range(1, 26), 15))
        draws.append({
            "concurso": i + 1,
            "data": f"{(i % 28) + 1:02d}/01/2010",
            "dezenas": dezenas,
        })
    return draws


@pytest.fixture
def small_draws():
    return _make_draws(100)


@pytest.fixture
def large_draws():
    return _make_draws(300)


# ── Binary matrix ─────────────────────────────────────────────────────────────

def test_binary_matrix_shape(small_draws):
    prep = LotofacilPreprocessor(small_draws)
    bm = prep._binary_matrix()
    assert bm.shape == (len(small_draws), TOTAL_NUMBERS)


def test_binary_matrix_values(small_draws):
    prep = LotofacilPreprocessor(small_draws)
    bm = prep._binary_matrix()
    # Each row should have exactly 15 ones
    assert np.all(bm.sum(axis=1) == 15)
    # Values should be 0 or 1
    assert set(np.unique(bm)).issubset({0.0, 1.0})


# ── prepare_dataset ────────────────────────────────────────────────────────────

def test_prepare_dataset_shapes(small_draws):
    prep = LotofacilPreprocessor(small_draws)
    X, y = prep.prepare_dataset()
    n = len(small_draws)
    assert X.shape[0] == n - 1
    assert y.shape == (n - 1, TOTAL_NUMBERS)


def test_prepare_dataset_target_shift(small_draws):
    """y[i] should be the binary vector of draw i+1 (not draw i)."""
    prep = LotofacilPreprocessor(small_draws)
    binary = prep._binary_matrix()
    _, y = prep.prepare_dataset()
    # y[0] should equal binary[1]
    np.testing.assert_array_equal(y[0], binary[1])
    # y[-1] should equal binary[-1]
    np.testing.assert_array_equal(y[-1], binary[-1])


def test_prepare_dataset_no_nan(small_draws):
    prep = LotofacilPreprocessor(small_draws)
    X, y = prep.prepare_dataset()
    assert not np.any(np.isnan(X))
    assert not np.any(np.isnan(y))


# ── Frequency windows ─────────────────────────────────────────────────────────

def test_sliding_frequency_range(small_draws):
    prep = LotofacilPreprocessor(small_draws)
    binary = prep._binary_matrix()
    freq = prep._sliding_frequency(binary, 30)
    # All values should be in [0, 1]
    assert np.all(freq >= 0) and np.all(freq <= 1)
    # Row 0 should be all zeros (no prior data)
    np.testing.assert_array_equal(freq[0], np.zeros(TOTAL_NUMBERS))


# ── Cyclic encoding ───────────────────────────────────────────────────────────

def test_temporal_features_cyclic(small_draws):
    prep = LotofacilPreprocessor(small_draws)
    feats = prep._temporal_features()
    assert feats.shape == (len(small_draws), 4)
    # sin/cos values in [-1, 1]
    assert np.all(feats >= -1.0) and np.all(feats <= 1.0)


# ── LSTM sequences ────────────────────────────────────────────────────────────

def test_prepare_lstm_sequences_shape(large_draws):
    prep = LotofacilPreprocessor(large_draws)
    seqs = prep.prepare_lstm_sequences(window_size=50)
    n = len(large_draws)
    assert seqs.shape == (n - 50, 50, TOTAL_NUMBERS)


def test_prepare_lstm_sequences_values(large_draws):
    prep = LotofacilPreprocessor(large_draws)
    seqs = prep.prepare_lstm_sequences(window_size=50)
    assert np.all(seqs >= 0) and np.all(seqs <= 1)


def test_get_latest_window_shape(large_draws):
    prep = LotofacilPreprocessor(large_draws)
    window = prep.get_latest_window(window_size=50)
    assert window.shape == (1, 50, TOTAL_NUMBERS)


def test_get_latest_window_pads_small_dataset():
    draws = _make_draws(20)
    prep = LotofacilPreprocessor(draws)
    window = prep.get_latest_window(window_size=50)
    assert window.shape == (1, 50, TOTAL_NUMBERS)
