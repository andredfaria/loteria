"""Tests for TransformerModel."""
import numpy as np
import pytest
from lotofacil_ml.data.loader import Draw


def _make_draws(n: int, seed: int = 0) -> list:
    import random
    rng = random.Random(seed)
    nums = list(range(1, 26))
    return [Draw(concurso=i + 1, data="01/01/2024", dezenas=sorted(rng.sample(nums, 15))) for i in range(n)]


def test_transformer_model_name():
    from lotofacil_ml.models.transformer_model import TransformerModel
    assert TransformerModel().name == "transformer"


def test_transformer_predict_proba_before_fit():
    from lotofacil_ml.models.transformer_model import TransformerModel
    model = TransformerModel()
    p = model.predict_proba()
    assert p.shape == (25,)
    assert np.allclose(p, p[0])  # uniform before fit


def test_transformer_fit_and_predict():
    from lotofacil_ml.models.transformer_model import TransformerModel
    draws = _make_draws(60)
    model = TransformerModel(window_size=5)
    model.fit(draws)
    p = model.predict_proba()
    assert p.shape == (25,)
    assert p.sum() > 0
    assert np.all(p >= 0) and np.all(p <= 1)


def test_transformer_select_top_15():
    from lotofacil_ml.models.transformer_model import TransformerModel
    draws = _make_draws(60)
    model = TransformerModel(window_size=5)
    model.fit(draws)
    top15 = model.select_top_15()
    assert len(top15) == 15
    assert all(1 <= n <= 25 for n in top15)
    assert len(set(top15)) == 15


def test_transformer_save_load(tmp_path):
    from lotofacil_ml.models.transformer_model import TransformerModel
    draws = _make_draws(60)
    model = TransformerModel(window_size=5)
    model.fit(draws)
    model.save(tmp_path)
    model2 = TransformerModel(window_size=5)
    model2.load(tmp_path)
    p = model2.predict_proba()
    assert p.shape == (25,)


def test_transformer_insufficient_draws():
    from lotofacil_ml.models.transformer_model import TransformerModel
    model = TransformerModel(window_size=50)
    draws = _make_draws(3)
    model.fit(draws)  # should log warning and return without training
    p = model.predict_proba()
    assert p.shape == (25,)
