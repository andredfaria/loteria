"""Tests for evaluation metrics."""

import pytest
from lotofacil_lab.evaluation.metrics import (
    mean_hits,
    hits_distribution,
    rate_ge,
    financial_metrics,
    vs_random_p_value,
)


@pytest.fixture
def mock_results():
    return [
        {"concurso": 1, "hits": 9},
        {"concurso": 2, "hits": 11},
        {"concurso": 3, "hits": 12},
        {"concurso": 4, "hits": 10},
        {"concurso": 5, "hits": 9},
    ]


def test_mean_hits(mock_results):
    assert mean_hits(mock_results) == pytest.approx((9 + 11 + 12 + 10 + 9) / 5)


def test_mean_hits_empty():
    assert mean_hits([]) == 0.0


def test_hits_distribution(mock_results):
    dist = hits_distribution(mock_results)
    assert dist[9] == 2
    assert dist[11] == 1
    assert dist[12] == 1
    assert dist[10] == 1


def test_rate_ge(mock_results):
    assert rate_ge(mock_results, 11) == pytest.approx(2 / 5)
    assert rate_ge(mock_results, 12) == pytest.approx(1 / 5)
    assert rate_ge(mock_results, 15) == 0.0


def test_financial_metrics_roi(mock_results):
    fin = financial_metrics(mock_results)
    assert "roi_pct" in fin
    assert "sharpe" in fin
    assert "max_drawdown" in fin
    assert "equity_curve" in fin
    assert len(fin["equity_curve"]) == len(mock_results)
    # 9+11+12+10+9 hits, prizes: 9→0, 11→7, 12→14
    expected_revenue = 7.0 + 14.0  # only 11 and 12 hits earn
    assert fin["total_revenue"] == pytest.approx(expected_revenue)


def test_financial_metrics_empty():
    fin = financial_metrics([])
    assert fin == {}


def test_vs_random_p_value_uniform():
    """A model hitting exactly 9.0 every time should have p ≈ 0.5."""
    hits = [9] * 100
    p = vs_random_p_value(hits)
    assert 0.3 < p < 0.7


def test_vs_random_p_value_strong_model():
    """A model always hitting 15 should have very small p-value."""
    hits = [15] * 100
    p = vs_random_p_value(hits)
    assert p < 1e-6


def test_vs_random_p_value_empty():
    assert vs_random_p_value([]) == 1.0
