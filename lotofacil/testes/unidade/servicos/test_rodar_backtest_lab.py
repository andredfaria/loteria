"""Tests for rodar_backtest_lab — leak-free walk-forward backtest wiring."""
import pytest

from lotofacil.dominio.entidades import Sorteio as Draw


def _draw(concurso: int) -> Draw:
    offset = concurso % 25
    dezenas = sorted(((offset + i) % 25) + 1 for i in range(15))
    return Draw(concurso=concurso, data="01/01/2020", dezenas=dezenas)


class _FakeNeuralModel:
    calls: list[list[int]] = []

    def __init__(self, cfg):
        self.cfg = cfg

    def fit(self, draws):
        _FakeNeuralModel.calls.append([d.concurso for d in draws])

    def predict(self, draws):
        return list(range(1, 16))

    @property
    def name(self):
        return "fake_neural"


@pytest.fixture(autouse=True)
def _reset_fake_calls():
    _FakeNeuralModel.calls = []
    yield


def test_rodar_backtest_lab_no_leakage(monkeypatch):
    from lotofacil.servicos import rodar_backtest_lab as module

    draws = [_draw(c) for c in range(1, 351)]
    monkeypatch.setattr(module, "load_draws", lambda: draws)
    monkeypatch.setattr(
        "lotofacil.experimentos.experiments.runner.NeuralModular", _FakeNeuralModel
    )

    resultado = module.rodar_backtest_lab(
        configs=["base+temp+priors"],
        start_concurso=340,
        end_concurso=350,
        retrain_every=1,
    )

    assert resultado.warnings == []
    assert _FakeNeuralModel.calls, "modelo fake nunca foi treinado"
    for k, call_concursos in enumerate(_FakeNeuralModel.calls):
        test_concurso = 340 + k
        assert max(call_concursos) < test_concurso, (
            f"vazamento: treino do passo {k} viu concurso {max(call_concursos)} "
            f"ao prever o concurso {test_concurso}"
        )

    entry = next(
        e for e in resultado.report["results"] if e["name"] == "neural_base+temp+priors"
    )
    assert entry["n_evaluated"] == 11
    assert "error" not in entry


def test_rodar_backtest_lab_shifts_start_when_history_insufficient(monkeypatch):
    from lotofacil.servicos import rodar_backtest_lab as module

    draws = [_draw(c) for c in range(1, 351)]
    monkeypatch.setattr(module, "load_draws", lambda: draws)
    monkeypatch.setattr(
        "lotofacil.experimentos.experiments.runner.NeuralModular", _FakeNeuralModel
    )

    resultado = module.rodar_backtest_lab(
        configs=["base+temp+priors"],
        start_concurso=5,
        end_concurso=310,
        retrain_every=50,
    )

    assert resultado.warnings
    assert "301" in resultado.warnings[0]


def test_rejects_empty_configs():
    from lotofacil.servicos.rodar_backtest_lab import rodar_backtest_lab

    with pytest.raises(ValueError, match="ao menos uma config"):
        rodar_backtest_lab([], 100, 200)


def test_rejects_start_not_less_than_end():
    from lotofacil.servicos.rodar_backtest_lab import rodar_backtest_lab

    with pytest.raises(ValueError, match="menor que"):
        rodar_backtest_lab(["base+temp+priors"], 200, 100)


def test_rejects_unknown_config_signature(monkeypatch):
    from lotofacil.servicos import rodar_backtest_lab as module

    with pytest.raises(ValueError, match="inválid"):
        module.rodar_backtest_lab(["nao_existe"], 100, 200)


def test_rejects_end_beyond_available_data(monkeypatch):
    from lotofacil.servicos import rodar_backtest_lab as module

    draws = [_draw(c) for c in range(1, 351)]
    monkeypatch.setattr(module, "load_draws", lambda: draws)

    with pytest.raises(ValueError, match="último concurso disponível"):
        module.rodar_backtest_lab(["base+temp+priors"], 340, 9999)
