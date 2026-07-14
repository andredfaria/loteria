from __future__ import annotations

import pytest

from quina.dominio.entidades import Sorteio
from quina.infra.atributos.base import (
    freq_k,
    atraso,
    stats_soma,
    stats_pares,
    repeticao_media,
    consecutivos_media,
    std_frequencias,
)


@pytest.fixture
def sample_draws():
    return [Sorteio(concurso=i + 1, data=f"01/01/2020", dezenas=list(range((i % 16) + 1, (i % 16) + 6))) for i in range(100)]


class TestFreqK:
    def test_returns_dict_with_80_keys(self, sample_draws):
        result = freq_k(sample_draws, idx=50, k=10)
        assert len(result) == 80
        assert all(1 <= k <= 80 for k in result)

    def test_sum_is_1(self, sample_draws):
        result = freq_k(sample_draws, idx=50, k=30)
        assert abs(sum(result.values()) - 5.0) < 0.1

    def test_zero_draws_returns_zeros(self, sample_draws):
        result = freq_k(sample_draws, idx=0, k=10)
        assert all(v == 0.0 for v in result.values())


class TestAtraso:
    def test_returns_80_keys(self, sample_draws):
        result = atraso(sample_draws, idx=50)
        assert len(result) == 80

    def test_capped_at_max(self, sample_draws):
        result = atraso(sample_draws, idx=50, max_atraso=10)
        assert all(v <= 10 for v in result.values())


class TestStatsSoma:
    def test_returns_mean_median_std(self, sample_draws):
        result = stats_soma(sample_draws, idx=50, k=10)
        assert "mean" in result
        assert "median" in result
        assert "std" in result

    def test_empty_window_returns_zeros(self, sample_draws):
        result = stats_soma(sample_draws, idx=0, k=10)
        assert result["mean"] == 0.0


class TestStatsPares:
    def test_sum_is_5(self, sample_draws):
        mp, mi = stats_pares(sample_draws, idx=50, k=10)
        assert abs(mp + mi - 5.0) < 0.01


class TestStdFrequencias:
    def test_non_negative(self, sample_draws):
        fk = freq_k(sample_draws, idx=50, k=30)
        result = std_frequencias(fk)
        assert result >= 0.0