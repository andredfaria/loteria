"""Tests for confusion matrix computations."""
import random
import numpy as np
import pytest


def _make_results_with_probas(hits_list, seed=0):
    """Synthetic results with uniform probas."""
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


def test_confusion_per_number_perfect():
    from lotofacil_ml.evaluation.confusion import confusion_per_number
    results = []
    actual = list(range(1, 16))
    results.append({"predicted": actual, "actual": actual, "hits": 15, "probas": None})
    cm = confusion_per_number(results)
    agg = cm["aggregate"]
    assert agg["TP"] == 15
    assert agg["FP"] == 0
    assert agg["FN"] == 0
    assert agg["TN"] == 10
    assert cm["precision"] == pytest.approx(1.0)
    assert cm["recall"] == pytest.approx(1.0)
    assert cm["f1"] == pytest.approx(1.0)


def test_confusion_per_number_zero_hits():
    from lotofacil_ml.evaluation.confusion import confusion_per_number
    actual = list(range(1, 16))
    predicted = list(range(16, 31))
    results = [{"predicted": predicted, "actual": actual, "hits": 0, "probas": None}]
    cm = confusion_per_number(results)
    agg = cm["aggregate"]
    assert agg["TP"] == 0
    assert agg["FP"] == 15
    assert agg["FN"] == 15
    assert cm["precision"] == pytest.approx(0.0)
    assert cm["recall"] == pytest.approx(0.0)
    assert cm["f1"] == pytest.approx(0.0)


def test_confusion_per_number_has_25_entries():
    from lotofacil_ml.evaluation.confusion import confusion_per_number
    results = _make_results_with_probas([12, 13, 11])
    cm = confusion_per_number(results)
    assert len(cm["per_number"]) == 25


def test_confusion_per_number_empty():
    from lotofacil_ml.evaluation.confusion import confusion_per_number
    cm = confusion_per_number([])
    assert cm["aggregate"]["TP"] == 0
    assert cm["precision"] == pytest.approx(0.0)


def test_confusion_per_number_f1_per_number_bounded():
    from lotofacil_ml.evaluation.confusion import confusion_per_number
    results = _make_results_with_probas([9, 10, 11, 12])
    cm = confusion_per_number(results)
    for n, data in cm["per_number"].items():
        assert 0.0 <= data["F1"] <= 1.0


def test_confusion_by_hits_returns_required_keys():
    from lotofacil_ml.evaluation.confusion import confusion_by_hits
    results = _make_results_with_probas([9, 10, 11, 12, 13])
    out = confusion_by_hits(results)
    assert "actual_distribution" in out
    assert "expected_distribution" in out
    assert "matrix" in out


def test_confusion_by_hits_bucket_keys():
    from lotofacil_ml.evaluation.confusion import confusion_by_hits
    results = _make_results_with_probas([11, 12, 13])
    out = confusion_by_hits(results)
    for key in (0, 11, 12, 13, 14, 15):
        assert key in out["actual_distribution"]


def test_confusion_by_hits_counts_are_correct():
    from lotofacil_ml.evaluation.confusion import confusion_by_hits
    results = _make_results_with_probas([11, 12, 9, 8])
    out = confusion_by_hits(results)
    dist = out["actual_distribution"]
    assert dist[11] == 1
    assert dist[12] == 1
    assert dist[0] == 2


def test_confusion_by_hits_empty():
    from lotofacil_ml.evaluation.confusion import confusion_by_hits
    out = confusion_by_hits([])
    assert out["actual_distribution"][0] == 0
