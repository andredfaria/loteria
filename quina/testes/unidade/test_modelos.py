from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import pytest

from quina.dominio.entidades import Sorteio
from quina.infra.modelos.frequency_model import FrequencyModel
from quina.infra.modelos.frequency_ensemble import FrequencyEnsembleModel
from quina.infra.modelos.probabilistic import ProbabilisticModel


@pytest.fixture
def draws_50():
    return [Sorteio(concurso=i + 1, data="01/01/2020", dezenas=[1, 2, 3, 4, 5]) for i in range(50)]


class TestFrequencyModel:
    def test_fit_predict_proba_shape(self, draws_50):
        m = FrequencyModel()
        m.fit(draws_50)
        p = m.predict_proba()
        assert p.shape == (80,)
        assert np.isclose(p.sum(), 5.0, atol=0.01)

    def test_select_top_5_returns_5(self, draws_50):
        m = FrequencyModel()
        m.fit(draws_50)
        top5 = m.select_top_5()
        assert len(top5) == 5
        assert all(1 <= n <= 80 for n in top5)

    def test_save_load_roundtrip(self, draws_50):
        m = FrequencyModel()
        m.fit(draws_50)
        with TemporaryDirectory() as tmp:
            path = Path(tmp)
            m.save(path)
            m2 = FrequencyModel()
            m2.load(path)
            assert np.allclose(m.predict_proba(), m2.predict_proba())

    def test_name(self):
        assert FrequencyModel().name == "frequencia"


class TestFrequencyEnsembleModel:
    def test_fit_predict_proba_shape(self, draws_50):
        m = FrequencyEnsembleModel()
        m.fit(draws_50)
        p = m.predict_proba()
        assert p.shape == (80,)
        assert np.allclose(p.sum(), 5.0, atol=0.01)

    def test_name(self):
        assert FrequencyEnsembleModel().name == "frequencia_ensemble"


class TestProbabilisticModel:
    def test_fit_predict_proba_shape(self, draws_50):
        m = ProbabilisticModel()
        m.fit(draws_50)
        p = m.predict_proba()
        assert p.shape == (80,)

    def test_name(self):
        assert ProbabilisticModel().name == "probabilistico"