"""Tests for new KPI metric functions."""
import random
import numpy as np
import pytest


def _make_results(hits_list, seed=42):
    rng = random.Random(seed)
    all_nums = list(range(1, 26))
    results = []
    for hits in hits_list:
        actual = sorted(rng.sample(all_nums, 15))
        correct = actual[:hits]
        wrong_pool = [n for n in all_nums if n not in actual]
        wrong = rng.sample(wrong_pool, 15 - hits)
        predicted = sorted(correct + wrong)
        probas = np.full(25, 1.0 / 25, dtype=np.float32)
        results.append({
            "predicted": predicted,
            "actual": actual,
            "hits": hits,
            "probas": probas,
        })
    return results


# ── rmse_expected_hits ────────────────────────────────────────────────────────

def test_rmse_expected_hits_empty():
    from lotofacil_ml.evaluation.metrics import rmse_expected_hits
    assert rmse_expected_hits([]) == pytest.approx(0.0)


def test_rmse_expected_hits_uniform_probas():
    from lotofacil_ml.evaluation.metrics import rmse_expected_hits
    results = _make_results([9] * 10)
    rmse = rmse_expected_hits(results)
    assert rmse >= 0.0


def test_rmse_expected_hits_perfect_model():
    from lotofacil_ml.evaluation.metrics import rmse_expected_hits
    actual = list(range(1, 16))
    probas = np.zeros(25, dtype=np.float32)
    for n in actual:
        probas[n - 1] = 1.0
    results = [{"predicted": actual, "actual": actual, "hits": 15, "probas": probas}]
    assert rmse_expected_hits(results) == pytest.approx(0.0, abs=1e-5)


def test_rmse_expected_hits_without_probas():
    from lotofacil_ml.evaluation.metrics import rmse_expected_hits
    actual = list(range(1, 16))
    results = [{"predicted": actual, "actual": actual, "hits": 15, "probas": None}]
    assert rmse_expected_hits(results) == pytest.approx(0.0, abs=1e-5)


# ── mae_expected_hits ─────────────────────────────────────────────────────────

def test_mae_expected_hits_empty():
    from lotofacil_ml.evaluation.metrics import mae_expected_hits
    assert mae_expected_hits([]) == pytest.approx(0.0)


def test_mae_expected_hits_perfect_model():
    from lotofacil_ml.evaluation.metrics import mae_expected_hits
    actual = list(range(1, 16))
    probas = np.zeros(25, dtype=np.float32)
    for n in actual:
        probas[n - 1] = 1.0
    results = [{"predicted": actual, "actual": actual, "hits": 15, "probas": probas}]
    assert mae_expected_hits(results) == pytest.approx(0.0, abs=1e-5)


# ── roc_auc_per_number ────────────────────────────────────────────────────────

def test_roc_auc_per_number_returns_structure():
    from lotofacil_ml.evaluation.metrics import roc_auc_per_number
    results = _make_results([9, 10, 11, 12, 11, 10])
    out = roc_auc_per_number(results)
    assert "mean" in out
    assert "std" in out
    assert "per_number" in out
    assert len(out["per_number"]) == 25


def test_roc_auc_per_number_mean_bounded():
    from lotofacil_ml.evaluation.metrics import roc_auc_per_number
    results = _make_results([9, 10, 11, 12, 11, 10])
    out = roc_auc_per_number(results)
    assert 0.0 <= out["mean"] <= 1.0
    assert out["std"] >= 0.0


def test_roc_auc_per_number_empty():
    from lotofacil_ml.evaluation.metrics import roc_auc_per_number
    out = roc_auc_per_number([])
    assert out["mean"] == pytest.approx(0.5)


def test_roc_auc_per_number_perfect_model():
    from lotofacil_ml.evaluation.metrics import roc_auc_per_number
    import random as rnd
    rng = rnd.Random(1)
    all_nums = list(range(1, 26))
    results = []
    for _ in range(20):
        actual = sorted(rng.sample(all_nums, 15))
        probas = np.zeros(25, dtype=np.float32)
        for n in actual:
            probas[n - 1] = 1.0
        results.append({
            "predicted": actual, "actual": actual, "hits": 15, "probas": probas,
        })
    out = roc_auc_per_number(results)
    assert out["mean"] >= 0.9
