import numpy as np
import pytest
from lotofacil_ml.data.loader import Draw
from lotofacil_ml.models.frequency_ensemble import FrequencyEnsembleModel


def _make_draws(n: int) -> list[Draw]:
    """Draws com dezenas fixas 1-15 para resultado determinístico."""
    return [Draw(concurso=i, data="01/01/2020", dezenas=list(range(1, 16))) for i in range(1, n + 1)]



def test_name():
    model = FrequencyEnsembleModel()
    assert model.name == "frequency_ensemble"


def test_predict_proba_shape():
    model = FrequencyEnsembleModel()
    model.fit(_make_draws(50))
    proba = model.predict_proba()
    assert proba.shape == (25,)
    assert proba.dtype == np.float32


def test_predict_proba_range():
    model = FrequencyEnsembleModel()
    model.fit(_make_draws(50))
    proba = model.predict_proba()
    assert proba.min() >= 0.0
    assert proba.max() <= 1.0


def test_select_top_15_returns_15_numbers():
    model = FrequencyEnsembleModel()
    model.fit(_make_draws(50))
    top15 = model.select_top_15()
    assert len(top15) == 15
    assert all(1 <= n <= 25 for n in top15)
    assert len(set(top15)) == 15


def test_fit_uses_all_windows_with_fewer_draws():
    """Se n < k, janela usa todos os draws disponíveis sem erro."""
    model = FrequencyEnsembleModel()
    model.fit(_make_draws(3))  # menos que k=5
    proba = model.predict_proba()
    assert proba.shape == (25,)


def test_scores_reflect_frequency():
    """Números 1-15 devem ter score maior que 16-25 após fit com draws fixos."""
    model = FrequencyEnsembleModel()
    model.fit(_make_draws(100))
    proba = model.predict_proba()
    avg_hot = proba[:15].mean()   # números 1-15 (índices 0-14)
    avg_cold = proba[15:].mean()  # números 16-25 (índices 15-24)
    assert avg_hot > avg_cold


def test_custom_windows():
    """Modelo aceita janelas customizadas."""
    model = FrequencyEnsembleModel(windows={10: 0.7, 30: 0.3})
    model.fit(_make_draws(50))
    proba = model.predict_proba()
    assert proba.shape == (25,)


def test_save_load(tmp_path):
    model = FrequencyEnsembleModel()
    draws = _make_draws(50)
    model.fit(draws)
    original = model.predict_proba().copy()

    model.save(tmp_path)
    loaded = FrequencyEnsembleModel()
    loaded.load(tmp_path)

    np.testing.assert_array_almost_equal(loaded.predict_proba(), original)


def test_all_window_key():
    """Chave 'all' funciona sem erro."""
    model = FrequencyEnsembleModel(windows={"all": 0.5, 30: 0.5})
    model.fit(_make_draws(50))
    proba = model.predict_proba()
    assert proba.shape == (25,)
