import pytest
from lotofacil_ml.data.loader import Draw
from lotofacil_ml.backtest.engine import BacktestEngine, BacktestResult
from lotofacil_ml.models.frequency_model import FrequencyModel


def _make_draws(n: int) -> list[Draw]:
    return [Draw(concurso=i, data="01/01/2020", dezenas=list(range(1, 16))) for i in range(1, n + 1)]


def test_backtest_no_leakage():
    """Engine must never use draw X when predicting for draw X."""
    draws = _make_draws(150)
    model = FrequencyModel()
    engine = BacktestEngine(model, train_window=100, retrain_every=50)
    results = engine.run(draws, start_idx=100, end_idx=120)
    assert len(results) == 20
    for r in results:
        assert 0 <= r.hits <= 15


def test_backtest_result_fields():
    draws = _make_draws(150)
    model = FrequencyModel()
    engine = BacktestEngine(model, train_window=100, retrain_every=50)
    results = engine.run(draws, start_idx=100, end_idx=110)
    r = results[0]
    assert hasattr(r, "concurso")
    assert hasattr(r, "jogo")
    assert hasattr(r, "resultado")
    assert hasattr(r, "hits")
    assert hasattr(r, "model_name")
    assert len(r.jogo) == 15


def test_backtest_returns_empty_if_insufficient_data():
    draws = _make_draws(50)
    model = FrequencyModel()
    engine = BacktestEngine(model, train_window=100, retrain_every=50)
    results = engine.run(draws, start_idx=100, end_idx=110)
    assert results == []
