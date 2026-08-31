"""O módulo de significância decide se um modelo "bate o aleatório".

Num projeto de loteria, um falso positivo aqui é o pior resultado possível:
é exatamente a afirmação que os disclaimers existem para impedir. Por isso
estes testes cobrem o viés do teste, não só o caminho feliz.
"""
from __future__ import annotations

import random

import pytest
from scipy import stats

from lotofacil.infra.avaliacao.significancia import (
    _ttest_paired,
    _normal_sf,
    compare_vs_baseline,
)


class TestTTestPareado:
    def test_bate_com_scipy(self):
        rng = random.Random(42)
        a = [rng.gauss(6.2, 1.0) for _ in range(40)]
        b = [rng.gauss(6.0, 1.0) for _ in range(40)]
        assert _ttest_paired(a, b) == pytest.approx(stats.ttest_rel(a, b).pvalue, rel=1e-9)

    def test_usa_t_e_nao_a_normal(self):
        """O bug corrigido: avaliar t na normal subestima o p-valor.

        Construímos uma amostra cujo t cai exatamente no crítico de 5% para
        df=29. O p correto é 0.05; a aproximação normal daria ~0.041 e
        declararia significância onde não há.
        """
        n = 30
        df = n - 1
        t_critico = stats.t.ppf(0.975, df)

        # diffs com média/desvio calibrados para produzir t == t_critico
        base = [i - (n - 1) / 2 for i in range(n)]           # média 0
        sd = (sum(x * x for x in base) / (n - 1)) ** 0.5
        alvo = t_critico * sd / (n ** 0.5)
        a = [alvo + x for x in base]
        b = [0.0] * n

        p = _ttest_paired(a, b)
        p_normal = 2 * _normal_sf(t_critico)

        assert p == pytest.approx(0.05, abs=1e-6), "p-valor deve vir da distribuição t"
        assert p_normal < 0.045, "sanidade: a normal realmente subestima"
        assert p > p_normal, "o t sempre dá p maior que a normal — nunca o contrário"

    def test_variancia_zero_nao_declara_significancia(self):
        a = [5.0] * 10
        b = [3.0] * 10
        assert _ttest_paired(a, b) == 1.0

    def test_amostra_minima(self):
        assert _ttest_paired([1.0], [0.0]) == 1.0


class TestCompareVsBaseline:
    def test_modelo_igual_ao_baseline_nao_e_significativo(self):
        hits = [6, 7, 5, 8, 6, 7, 6, 5, 7, 6] * 4      # n=40
        r = compare_vs_baseline(hits, list(hits))
        assert not r.significant
        assert r.test_used == "paired t-test"

    def test_amostra_pequena_usa_wilcoxon(self):
        r = compare_vs_baseline([6, 7, 5, 8, 6], [6, 6, 6, 6, 6])
        assert "Wilcoxon" in r.test_used
        assert r.statistical_confidence == "low"

    def test_dados_insuficientes(self):
        r = compare_vs_baseline([], [])
        assert r.p_value == 1.0
        assert r.status == "insufficient_data"

    def test_ruido_aleatorio_raramente_e_significativo(self):
        """Sob H0 verdadeira, a taxa de falsos positivos deve ficar perto de alpha.

        Se o teste estivesse enviesado (o bug antigo), esta taxa subiria acima
        de 5% de forma sistemática.
        """
        rng = random.Random(7)
        falsos_positivos = 0
        ensaios = 200
        for _ in range(ensaios):
            a = [rng.gauss(6.0, 1.5) for _ in range(40)]
            b = [rng.gauss(6.0, 1.5) for _ in range(40)]
            if compare_vs_baseline(a, b).significant:
                falsos_positivos += 1
        taxa = falsos_positivos / ensaios
        assert taxa <= 0.10, f"taxa de falso positivo {taxa:.1%} alta demais para alpha=5%"
