"""Tests for ValidationSuite."""
import numpy as np
import pytest
from lotofacil_ml.data.loader import Draw
from lotofacil_ml.models.base_model import BaseModel


def _make_draws(n: int = 200, seed: int = 0) -> list:
    import random
    rng = random.Random(seed)
    nums = list(range(1, 26))
    return [Draw(concurso=i + 1, data="01/01/2024", dezenas=sorted(rng.sample(nums, 15))) for i in range(n)]


class _ConstantModel(BaseModel):
    """Stub model that always returns uniform probabilities."""
    def __init__(self):
        self._p = np.full(25, 1.0 / 25, dtype=np.float32)

    @property
    def name(self) -> str:
        return "constant"

    def fit(self, draws):
        pass

    def predict_proba(self) -> np.ndarray:
        return self._p

    def save(self, path):
        pass

    def load(self, path):
        pass


def test_validation_suite_returns_report_per_model():
    from lotofacil_ml.evaluation.validation_suite import ValidationSuite
    draws = _make_draws(200)
    suite = ValidationSuite()
    reports = suite.run(draws, {"constant": _ConstantModel()}, n_backtest=20)
    assert "constant" in reports


def test_validation_suite_report_has_all_fields():
    from lotofacil_ml.evaluation.validation_suite import ValidationSuite, ModelReport
    draws = _make_draws(200)
    suite = ValidationSuite()
    reports = suite.run(draws, {"constant": _ConstantModel()}, n_backtest=20)
    r = reports["constant"]
    assert isinstance(r, ModelReport)
    assert r.mean_hits >= 0
    assert r.rmse >= 0
    assert r.mae >= 0
    assert 0 <= r.precision <= 1
    assert 0 <= r.recall <= 1
    assert 0 <= r.f1 <= 1
    assert 0 <= r.roc_auc_mean <= 1
    assert r.n_evaluated == 20


def test_validation_suite_confusion_aggregate_keys():
    from lotofacil_ml.evaluation.validation_suite import ValidationSuite
    draws = _make_draws(200)
    suite = ValidationSuite()
    reports = suite.run(draws, {"constant": _ConstantModel()}, n_backtest=10)
    agg = reports["constant"].confusion_aggregate
    assert "TP" in agg and "FP" in agg and "TN" in agg and "FN" in agg


def test_validation_suite_insufficient_data():
    from lotofacil_ml.evaluation.validation_suite import ValidationSuite
    draws = _make_draws(10)  # too few
    suite = ValidationSuite()
    with pytest.raises(ValueError):
        suite.run(draws, {"constant": _ConstantModel()}, n_backtest=5)
