"""Smoke test for ExperimentRunner (no neural, fast)."""

import pytest

from lotofacil_lab.experiments.runner import ExperimentRunner
from lotofacil_lab.data.feature_flags import FeatureConfig


def test_runner_baselines_only(sample_draws):
    """Runner with run_neural=False should return at least random+freq entries."""
    runner = ExperimentRunner(sample_draws, min_train=10)
    result = runner.run(n_test=5, retrain_every=5, run_neural=False)

    assert "results" in result
    names = [e["name"] for e in result["results"]]
    assert "random" in names
    assert "frequency" in names


def test_runner_result_structure(sample_draws):
    runner = ExperimentRunner(sample_draws, min_train=10)
    result = runner.run(n_test=5, retrain_every=5, run_neural=False)

    for entry in result["results"]:
        assert "name" in entry
        if "error" not in entry:
            assert "mean_hits" in entry
            assert "roi_pct" in entry
            assert "p_value_vs_random" in entry


def test_runner_sorted_by_hits(sample_draws):
    runner = ExperimentRunner(sample_draws, min_train=10)
    result = runner.run(n_test=5, retrain_every=5, run_neural=False)

    valid = [e for e in result["results"] if "error" not in e]
    hits = [e["mean_hits"] for e in valid]
    assert hits == sorted(hits, reverse=True)


def test_runner_period_filter(sample_draws):
    """Period filter should restrict to draws within range."""
    runner = ExperimentRunner(sample_draws, min_train=10)
    # concursos 1..50; restrict to 40..50
    result = runner.run(n_test=3, retrain_every=3, run_neural=False,
                        period_start=40, period_end=50)
    assert result["n_draws_total"] <= 11
