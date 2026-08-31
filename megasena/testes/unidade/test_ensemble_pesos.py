"""Os pesos do ensemble precisam significar o que prometem.

Antes do rank percentil, os submodelos entravam na soma em escalas
incompatíveis: `frequency` e `probabilistic` min-max normalizados (amplitude
~1,0) contra `ml` calibrado em torno de NUMEROS_POR_SORTEIO/TOTAL_NUMEROS
(amplitude ~0,15). O resultado é que `ml` tinha peso nominal 0,50 e influência
real de ~12%. Um contribuidor que ajustasse `_DEFAULT_WEIGHTS` mediria um
efeito que não bate com a intenção — o parâmetro documentado não descrevia o
comportamento.
"""
from __future__ import annotations

import numpy as np
import pytest

from megasena.infra.modelos.ensemble import _DEFAULT_WEIGHTS, _para_percentil

TOTAL = 60


class TestParaPercentil:
    def test_preserva_ordem(self):
        v = np.array([0.5, 0.1, 0.9, 0.3], dtype=np.float32)
        assert list(np.argsort(_para_percentil(v))) == list(np.argsort(v))

    def test_amplitude_sempre_unitaria(self):
        """É isso que torna o peso comparável entre submodelos."""
        rng = np.random.default_rng(3)
        for escala in (1.0, 0.15, 1e-4, 1e3):
            v = (rng.random(TOTAL) * escala).astype(np.float32)
            r = _para_percentil(v)
            assert r.min() == pytest.approx(0.0)
            assert r.max() == pytest.approx(1.0)

    def test_invariante_a_transformacao_monotona(self):
        rng = np.random.default_rng(5)
        v = rng.random(TOTAL).astype(np.float32)
        assert np.allclose(_para_percentil(v), _para_percentil(v * 7.5 + 100))

    def test_vetor_degenerado(self):
        assert _para_percentil(np.array([1.0], dtype=np.float32)).shape == (1,)


class TestCoerenciaPesoInfluencia:
    def test_influencia_bate_com_o_peso(self):
        """A propriedade que o bug quebrava: influência == peso declarado."""
        rng = np.random.default_rng(11)
        componentes = {
            "frequency": rng.random(TOTAL).astype(np.float32),
            "probabilistic": rng.random(TOTAL).astype(np.float32),
            # escala pequena de propósito: é o caso que quebrava antes
            "ml": (0.10 + 0.03 * rng.standard_normal(TOTAL)).astype(np.float32),
        }
        amplitudes = {
            nome: float((_para_percentil(v).max() - _para_percentil(v).min()) * _DEFAULT_WEIGHTS[nome])
            for nome, v in componentes.items()
        }
        total = sum(amplitudes.values())
        for nome, amp in amplitudes.items():
            influencia = amp / total
            assert influencia == pytest.approx(_DEFAULT_WEIGHTS[nome], abs=1e-6), (
                f"{nome}: peso {_DEFAULT_WEIGHTS[nome]} mas influência {influencia:.3f}"
            )

    def test_escala_bruta_quebraria_a_coerencia(self):
        """Guarda contra regressão: sem o percentil, a incoerência volta."""
        rng = np.random.default_rng(11)
        freq = rng.random(TOTAL).astype(np.float32)
        prob = rng.random(TOTAL).astype(np.float32)
        ml = (0.10 + 0.03 * rng.standard_normal(TOTAL)).astype(np.float32)
        bruto = {
            "frequency": float((freq.max() - freq.min()) * _DEFAULT_WEIGHTS["frequency"]),
            "ml": float((ml.max() - ml.min()) * _DEFAULT_WEIGHTS["ml"]),
            "probabilistic": float((prob.max() - prob.min()) * _DEFAULT_WEIGHTS["probabilistic"]),
        }
        total = sum(bruto.values())
        influencia_ml = bruto["ml"] / total
        assert influencia_ml < _DEFAULT_WEIGHTS["ml"] / 2, (
            "sem normalização o ml deveria estar MUITO abaixo do peso nominal; "
            "se este teste falhar, as escalas mudaram e o de cima precisa ser revisto"
        )
