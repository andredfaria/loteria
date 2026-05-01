"""Tests for LotofacilMetrics."""

import pytest

from lotofacil_ml.evaluation.metrics import LotofacilMetrics
from lotofacil_ml.config import NUMBERS_PER_DRAW, TOTAL_NUMBERS


# ── Fixtures ───────────────────────────────────────────────────────────────────

def _make_results(hits_list):
    """Create synthetic results with given hit counts."""
    import random
    rng = random.Random(0)
    all_nums = list(range(1, 26))
    results = []
    for hits in hits_list:
        actual = sorted(rng.sample(all_nums, 15))
        # Build predicted: `hits` correct + (15-hits) wrong
        correct = actual[:hits]
        wrong_pool = [n for n in all_nums if n not in actual]
        wrong = rng.sample(wrong_pool, 15 - hits)
        predicted = sorted(correct + wrong)
        results.append({"predicted": predicted, "actual": actual, "hits": hits})
    return results


@pytest.fixture
def perfect_results():
    """All 15 hits."""
    return _make_results([15] * 10)


@pytest.fixture
def mixed_results():
    return _make_results([11, 12, 13, 14, 15, 11, 12, 13, 14, 15])


@pytest.fixture
def low_results():
    return _make_results([9, 10, 10, 9, 8])


# ── distribution_of_hits ──────────────────────────────────────────────────────

def test_distribution_of_hits_perfect(perfect_results):
    dist = LotofacilMetrics.distribution_of_hits(perfect_results)
    assert dist[15] == 10
    assert dist[14] == 0
    assert dist[11] == 0


def test_distribution_of_hits_mixed(mixed_results):
    dist = LotofacilMetrics.distribution_of_hits(mixed_results)
    assert dist[11] == 2
    assert dist[12] == 2
    assert dist[15] == 2


def test_distribution_of_hits_below_threshold(low_results):
    """Hits below 11 are not counted in the distribution."""
    dist = LotofacilMetrics.distribution_of_hits(low_results)
    assert all(v == 0 for v in dist.values())


def test_distribution_of_hits_empty():
    dist = LotofacilMetrics.distribution_of_hits([])
    assert all(v == 0 for v in dist.values())


# ── mean_accuracy ─────────────────────────────────────────────────────────────

def test_mean_accuracy_perfect(perfect_results):
    acc = LotofacilMetrics.mean_accuracy(perfect_results)
    assert acc == 15.0


def test_mean_accuracy_mixed(mixed_results):
    acc = LotofacilMetrics.mean_accuracy(mixed_results)
    assert acc == pytest.approx((11 + 12 + 13 + 14 + 15) * 2 / 10, rel=1e-3)


def test_mean_accuracy_empty():
    assert LotofacilMetrics.mean_accuracy([]) == 0.0


# ── recall_precision ──────────────────────────────────────────────────────────

def test_recall_precision_perfect(perfect_results):
    rp = LotofacilMetrics.recall_precision(perfect_results)
    assert rp["recall"] == pytest.approx(1.0)
    assert rp["precision"] == pytest.approx(1.0)


def test_recall_precision_empty():
    rp = LotofacilMetrics.recall_precision([])
    assert rp["recall"] == 0.0
    assert rp["precision"] == 0.0


def test_recall_precision_bounds(mixed_results):
    rp = LotofacilMetrics.recall_precision(mixed_results)
    assert 0.0 <= rp["recall"] <= 1.0
    assert 0.0 <= rp["precision"] <= 1.0


# ── vs_random_baseline ────────────────────────────────────────────────────────

def test_vs_random_baseline_returns_all_keys(mixed_results):
    baseline = LotofacilMetrics.vs_random_baseline(mixed_results, n_simulations=50)
    assert "model_mean" in baseline
    assert "random_mean" in baseline
    assert "improvement_pct" in baseline
    assert "p_value" in baseline


def test_vs_random_baseline_random_near_9(mixed_results):
    """Random baseline for 15 picks out of 25 should be ~9."""
    baseline = LotofacilMetrics.vs_random_baseline(mixed_results, n_simulations=500)
    # Expected hits = 15 * 15/25 = 9
    assert 7.0 <= baseline["random_mean"] <= 11.0


def test_vs_random_baseline_perfect_beats_random(perfect_results):
    baseline = LotofacilMetrics.vs_random_baseline(perfect_results, n_simulations=100)
    assert baseline["model_mean"] > baseline["random_mean"]
    assert baseline["improvement_pct"] > 0
