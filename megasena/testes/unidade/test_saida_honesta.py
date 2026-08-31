"""Testes de regressão para F-02: o score do ensemble não pode ser exibido
como se fosse uma probabilidade estatística.

O treino real do ensemble (RandomForest + XGBoost + LightGBM) é lento demais
para um teste unitário (~1 min mesmo com poucos sorteios), então os testes
que exercitam o CLI usam um duplo de teste (monkeypatch) para `fit`/`save`/
`load`/`score`/`score_dict` do `EnsemblePredictor`, evitando o treino real.
"""
from __future__ import annotations

import random
import warnings

import numpy as np
import pytest
from typer.testing import CliRunner

from megasena.dominio.entidades import Sorteio
from megasena.infra.config import NUMEROS_POR_SORTEIO, TOTAL_NUMEROS
from megasena.infra.modelos.ensemble import EnsemblePredictor
from megasena.infra.modelos.frequency_ensemble import FrequencyEnsembleModel
from megasena.interface.cli import modelo as modelo_cli

runner = CliRunner()

# Probabilidade real de qualquer número sair em um sorteio — não depende do
# modelo, é sempre esta fração fixa. Calculada a partir das constantes do
# projeto (não hardcoded), como o próprio código de produção faz.
PROB_REAL_PCT = NUMEROS_POR_SORTEIO / TOTAL_NUMEROS * 100


def _draws(n: int = 60) -> list[Sorteio]:
    rng = random.Random(42)
    return [
        Sorteio(
            concurso=i + 1,
            data="01/01/2020",
            dezenas=sorted(rng.sample(range(1, TOTAL_NUMEROS + 1), NUMEROS_POR_SORTEIO)),
        )
        for i in range(n)
    ]


def _fake_scores() -> np.ndarray:
    rng = np.random.default_rng(7)
    arr = rng.random(TOTAL_NUMEROS).astype(np.float32)
    lo, hi = arr.min(), arr.max()
    return ((arr - lo) / (hi - lo)).astype(np.float32)  # min-max, topo = 1.0, como nos modelos reais


@pytest.fixture(autouse=True)
def _ensemble_rapido(monkeypatch):
    """Substitui o treino real do ensemble por um duplo de teste determinístico."""
    scores = _fake_scores()
    scores_dict = {i + 1: float(scores[i]) for i in range(TOTAL_NUMEROS)}

    monkeypatch.setattr(EnsemblePredictor, "fit", lambda self, draws: setattr(self, "_fitted", True))
    monkeypatch.setattr(EnsemblePredictor, "save", lambda self: None)
    monkeypatch.setattr(EnsemblePredictor, "load", lambda self: None)
    monkeypatch.setattr(EnsemblePredictor, "score", lambda self: scores.copy())
    monkeypatch.setattr(EnsemblePredictor, "score_dict", lambda self: dict(scores_dict))
    monkeypatch.setattr(modelo_cli, "load_draws", lambda _dir: _draws())
    yield


class TestTreinarSaidaHonesta:
    def test_nao_chama_score_do_modelo_de_probabilidade(self):
        result = runner.invoke(modelo_cli.app, ["treinar"])
        assert result.exit_code == 0, result.output
        assert "Top 10 Números por Probabilidade" not in result.output
        assert "Score (0-100)" in result.output
        assert "Probabilidade Real" in result.output

    def test_mostra_probabilidade_real_ancora(self):
        result = runner.invoke(modelo_cli.app, ["treinar"])
        assert result.exit_code == 0, result.output
        assert f"{PROB_REAL_PCT:.2f}%" in result.output


class TestPreverSaidaHonesta:
    def test_nao_chama_score_do_modelo_de_probabilidade(self):
        result = runner.invoke(modelo_cli.app, ["prever"])
        assert result.exit_code == 0, result.output
        assert "Probabilidade de cada número" not in result.output
        assert "Score de cada número (0-100)" in result.output

    def test_mostra_probabilidade_real_ancora(self):
        result = runner.invoke(modelo_cli.app, ["prever"])
        assert result.exit_code == 0, result.output
        assert f"{PROB_REAL_PCT:.2f}%" in result.output

    def test_score_de_otimizacao_nao_e_chamado_de_chance_de_acerto(self):
        result = runner.invoke(modelo_cli.app, ["prever"])
        assert result.exit_code == 0, result.output
        assert "aderência aos critérios" in result.output


class TestProbasSaidaHonesta:
    def test_nao_chama_score_do_modelo_de_probabilidade(self):
        result = runner.invoke(modelo_cli.app, ["probas"])
        assert result.exit_code == 0, result.output
        assert "Probabilidades por Número" not in result.output
        assert "Prob. ML" not in result.output
        assert "Score (0-100)" in result.output
        assert "Probabilidade Real" in result.output

    def test_probabilidade_real_e_constante_para_todos_os_numeros(self):
        result = runner.invoke(modelo_cli.app, ["probas"])
        assert result.exit_code == 0, result.output
        # a probabilidade real aparece uma vez por número (linha da tabela),
        # sempre com o mesmo valor — reforça que nenhum número é "mais provável"
        assert result.output.count(f"{PROB_REAL_PCT:.2f}%") >= TOTAL_NUMEROS


class TestAliasDepreciado:
    """`predict_proba()`/`predict_proba_dict()` continuam funcionando, mas
    emitem DeprecationWarning e delegam para `score()`/`score_dict()`.
    """

    def test_frequency_ensemble_predict_proba_ainda_funciona_e_avisa(self):
        m = FrequencyEnsembleModel()
        m.fit(_draws())
        with pytest.warns(DeprecationWarning):
            p = m.predict_proba()
        assert np.allclose(p, m.score())

    def test_ensemble_predict_proba_ainda_funciona_e_avisa(self):
        p = EnsemblePredictor()
        p.fit(_draws())  # duplo de teste via fixture autouse

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            arr = p.predict_proba()
        assert any(issubclass(w.category, DeprecationWarning) for w in caught)
        assert np.allclose(arr, p.score())

    def test_ensemble_predict_proba_dict_ainda_funciona_e_avisa(self):
        p = EnsemblePredictor()
        p.fit(_draws())

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            d = p.predict_proba_dict()
        assert any(issubclass(w.category, DeprecationWarning) for w in caught)
        assert d == p.score_dict()
