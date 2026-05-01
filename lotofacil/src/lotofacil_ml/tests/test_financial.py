import pytest
from lotofacil_ml.backtest.financial import FinancialSimulator, FinancialResult


def test_financial_no_wins():
    sim = FinancialSimulator(cost_per_game=3.0, prize_table={11: 7.0, 15: 1_500_000.0})
    results = [{"hits": 9}, {"hits": 10}, {"hits": 8}]
    fr = sim.simulate(results)
    assert fr.total_cost == pytest.approx(9.0)
    assert fr.total_revenue == pytest.approx(0.0)
    assert fr.net_profit == pytest.approx(-9.0)
    assert fr.roi_pct == pytest.approx(-100.0)


def test_financial_all_11():
    sim = FinancialSimulator(cost_per_game=3.0, prize_table={11: 7.0})
    results = [{"hits": 11}] * 10
    fr = sim.simulate(results)
    assert fr.total_cost == pytest.approx(30.0)
    assert fr.total_revenue == pytest.approx(70.0)
    assert fr.net_profit == pytest.approx(40.0)


def test_financial_drawdown():
    sim = FinancialSimulator(cost_per_game=3.0, prize_table={11: 7.0})
    # 5 losses then 1 win
    results = [{"hits": 5}] * 5 + [{"hits": 11}]
    fr = sim.simulate(results)
    assert fr.max_drawdown < 0  # must be negative (loss)


def test_financial_equity_curve_length():
    sim = FinancialSimulator(cost_per_game=3.0, prize_table={11: 7.0})
    results = [{"hits": i % 16} for i in range(20)]
    fr = sim.simulate(results)
    assert len(fr.equity_curve) == 20
