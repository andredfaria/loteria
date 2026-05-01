import pytest
from lotofacil_ml.evaluation.significance import compare_vs_baseline, SignificanceResult


def test_no_difference_returns_high_pvalue():
    # Same hits for both — t-test should give p close to 1
    model_hits = [9] * 100
    baseline_hits = [9] * 100
    result = compare_vs_baseline(model_hits, baseline_hits)
    assert result.p_value > 0.05


def test_clear_difference_returns_low_pvalue():
    import random
    rng = random.Random(42)
    model_hits = [rng.randint(12, 15) for _ in range(200)]
    baseline_hits = [rng.randint(8, 10) for _ in range(200)]
    result = compare_vs_baseline(model_hits, baseline_hits)
    assert result.p_value < 0.05
    assert result.model_mean > result.baseline_mean


def test_result_has_interpretation():
    model_hits = [9] * 50
    baseline_hits = [9] * 50
    result = compare_vs_baseline(model_hits, baseline_hits)
    assert isinstance(result.interpretation, str)
    assert len(result.interpretation) > 0


def test_result_fields():
    result = compare_vs_baseline([10, 11, 9], [9, 8, 10])
    assert hasattr(result, "model_mean")
    assert hasattr(result, "baseline_mean")
    assert hasattr(result, "improvement_pct")
    assert hasattr(result, "p_value")
    assert hasattr(result, "test_used")
