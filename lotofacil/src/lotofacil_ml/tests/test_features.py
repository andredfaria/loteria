import pytest
from lotofacil_ml.data.loader import Draw
from lotofacil_ml.features.base import (
    freq_k,
    atraso,
    stats_soma,
    stats_pares,
    repeticao_media,
    consecutivos_media,
    std_frequencias,
    ratio_moldura_miolo,
)


def _make_draws(n: int) -> list[Draw]:
    """n draws, all with dezenas 1-15."""
    return [Draw(concurso=i, data="01/01/2020", dezenas=list(range(1, 16))) for i in range(1, n + 1)]


def test_freq_k_uses_only_previous_draws():
    draws = _make_draws(30)
    # At idx=25 with k=5, window is draws[20:25] — all have 1-15
    result = freq_k(draws, idx=25, k=5)
    assert result[1] == 1.0   # number 1 appeared in all 5
    assert result[25] == 0.0  # number 25 never appeared


def test_freq_k_returns_proportions():
    draws = _make_draws(25)
    result = freq_k(draws, idx=25, k=10)
    for v in result.values():
        assert 0.0 <= v <= 1.0


def test_atraso_zero_when_appeared_last_draw():
    draws = _make_draws(25)
    result = atraso(draws, idx=25)
    # number 1 appeared in draws[24] (idx=24, the one before idx=25)
    assert result[1] == 0


def test_atraso_capped_at_max():
    draws = _make_draws(25)
    # number 25 never appeared (all draws have 1-15)
    result = atraso(draws, idx=25, max_atraso=20)
    assert result[25] == 20


def test_stats_soma_returns_dict():
    draws = _make_draws(25)
    result = stats_soma(draws, idx=25, k=10)
    assert "mean" in result and "median" in result and "std" in result
    # sum of 1..15 = 120
    assert result["mean"] == pytest.approx(120.0)


def test_stats_pares():
    draws = _make_draws(10)
    mean_pares, mean_impares = stats_pares(draws, idx=10, k=5)
    # dezenas 1-15: pares = 2,4,6,8,10,12,14 = 7; impares = 1,3,5,7,9,11,13,15 = 8
    assert mean_pares == pytest.approx(7.0)
    assert mean_impares == pytest.approx(8.0)


def test_ratio_moldura_miolo():
    # Last draw (at idx-1=4) has dezenas 1-15
    # moldura = {1,2,3,4,5} ∩ {1-15} = 5 numbers; miolo = 10; ratio = 5/10 = 0.5
    draws = _make_draws(5)
    result = ratio_moldura_miolo(draws, idx=5)
    assert result == pytest.approx(0.5)


from lotofacil_ml.features.advanced import (
    coocorrencia_score,
    trend_score,
    volatilidade_score,
    faixa_dominante,
    par_quente_score,
)


def test_coocorrencia_score_keys():
    draws = _make_draws(35)
    result = coocorrencia_score(draws, idx=35, k=30)
    assert set(result.keys()) == set(range(1, 26))
    assert all(v >= 0 for v in result.values())
    # numbers 1-15 appear in all draws; 16-25 never appear
    assert result[1] > 0
    assert result[25] == 0.0


def test_trend_score_positive_for_frequent_number():
    # All draws have number 1 in last 5 but not in previous 15 → positive trend
    base = [Draw(concurso=i, data="01/01/2020", dezenas=list(range(2, 17))) for i in range(1, 21)]
    recent = [Draw(concurso=20 + i, data="01/01/2020", dezenas=[1] + list(range(2, 16))) for i in range(1, 6)]
    draws = base + recent
    result = trend_score(draws, idx=25)
    assert result[1] > 0  # number 1 more frequent recently


def test_volatilidade_score_keys():
    draws = _make_draws(55)
    result = volatilidade_score(draws, idx=55, outer_k=50, inner_k=10)
    assert set(result.keys()) == set(range(1, 26))


def test_faixa_dominante():
    # draw at idx-1 has dezenas 1-15; faixa 1 (1-5) has 5, faixa 2 (6-10) has 5, faixa 3 (11-15) has 5
    draws = _make_draws(5)
    result = faixa_dominante(draws, idx=5)
    assert 1 <= result <= 5


def test_par_quente_score_is_int():
    draws = _make_draws(35)
    result = par_quente_score(draws, idx=35, k=30)
    assert isinstance(result, (int, float))
    assert result >= 0


def test_faixa_dominante_idx_zero():
    assert faixa_dominante([], idx=0) == 1


from lotofacil_ml.features.builder import FeatureBuilder
import numpy as np


def test_builder_no_leakage():
    draws = _make_draws(30)
    builder = FeatureBuilder()
    X, y = builder.build_dataset(draws)
    # With 30 draws and _MIN_IDX=20, we get 10 samples
    assert X.shape[0] == 10
    assert y.shape == (10, 25)


def test_builder_no_leakage_actual():
    from lotofacil_ml.features.builder import _MIN_IDX
    # History draws have dezenas 1-15; target draw at _MIN_IDX has 11-25
    history = _make_draws(_MIN_IDX)  # draws[0.._MIN_IDX-1], dezenas 1-15
    target = Draw(concurso=_MIN_IDX + 1, data="01/01/2020", dezenas=list(range(11, 26)))
    draws = history + [target]
    builder = FeatureBuilder()
    X, y = builder.build_dataset(draws)
    # X[0] built from draws[:_MIN_IDX] (all 1-15); freq of number 25 in k=5 must be 0
    feat_idx = builder.feature_names.index("freq_25_k5")
    assert X[0, feat_idx] == 0.0
    # y[0] encodes the target: number 25 appeared → index 24 should be 1
    assert y[0, 24] == 1.0
    # number 1 did not appear in target → index 0 should be 0
    assert y[0, 0] == 0.0


def test_builder_y_is_binary():
    draws = _make_draws(25)
    builder = FeatureBuilder()
    X, y = builder.build_dataset(draws)
    assert set(y.flatten().tolist()).issubset({0.0, 1.0})


def test_builder_inference_shape():
    draws = _make_draws(25)
    builder = FeatureBuilder()
    x_inf = builder.build_inference(draws)
    assert x_inf.shape == (1, builder.n_features)


def test_builder_feature_names_length():
    draws = _make_draws(25)
    builder = FeatureBuilder()
    builder.build_dataset(draws)
    assert len(builder.feature_names) == builder.n_features
