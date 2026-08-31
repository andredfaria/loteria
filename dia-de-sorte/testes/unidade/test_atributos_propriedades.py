"""
Property-based regression tests for infra.atributos.

These target two classes of feature-engineering bugs found by inspection:

- F-04: a windowed feature (`volatilidade_score`) whose window did not track
  `idx`, so it froze into a constant once enough draws had accumulated.
- F-05: a feature (`coocorrencia_score`) that was mathematically an affine
  rescaling of `freq_k`, providing zero information beyond it despite its
  name promising pairwise co-occurrence structure.

Draws are synthetic and generated from a seeded RNG for determinism.
"""

from __future__ import annotations

import random
from typing import List

import numpy as np
import pytest

from diadesorte.dominio.entidades import Sorteio as Draw
from diadesorte.infra.atributos.advanced import (
    coocorrencia_score,
    trend_score,
    volatilidade_score,
)
from diadesorte.infra.atributos.builder import FeatureBuilder

TOTAL = 31
NUMEROS_POR_SORTEIO = 7
SEED = 1234
N_DRAWS = 250


def _synthetic_draws(n: int, seed: int = SEED) -> List[Draw]:
    rng = random.Random(seed)
    return [
        Draw(
            concurso=i + 1,
            data="01/01/2020",
            dezenas=sorted(rng.sample(range(1, TOTAL + 1), NUMEROS_POR_SORTEIO)),
        )
        for i in range(n)
    ]


def _with_mutated_draw(draws: List[Draw], pos: int) -> List[Draw]:
    """Return a copy of draws with the draw at `pos` replaced by a different one."""
    mutated = list(draws)
    original = mutated[pos]
    replacement_pool = sorted(set(range(1, TOTAL + 1)) - set(original.dezenas))
    mutated[pos] = Draw(
        concurso=original.concurso,
        data=original.data,
        dezenas=replacement_pool[:NUMEROS_POR_SORTEIO],
    )
    return mutated


@pytest.fixture(scope="module")
def draws() -> List[Draw]:
    return _synthetic_draws(N_DRAWS)


@pytest.fixture(scope="module")
def dataset(draws):
    fb = FeatureBuilder()
    X, y = fb.build_dataset(draws)
    return X, y, fb.feature_names


def test_no_constant_columns(dataset):
    """Regression test for F-04: every feature column must vary across rows."""
    X, _, names = dataset
    stds = X.std(axis=0)
    constant = [names[i] for i in range(X.shape[1]) if stds[i] == 0]
    assert not constant, f"constant columns found: {constant}"


def test_no_near_duplicate_columns(dataset):
    """
    Regression test for F-05: no feature column should be an affine
    rescaling of another (coocorrencia_score used to be freq_k rescaled).

    `impares_mean_*` columns are excluded on purpose: by construction
    impares_mean = NUMEROS_POR_SORTEIO - pares_mean (see base.stats_pares),
    a deliberate, harmless design identity unrelated to F-04/F-05.
    """
    X, _, names = dataset
    keep = [i for i, nm in enumerate(names) if not nm.startswith("impares_mean")]
    sub = X[:, keep]
    corr = np.corrcoef(sub, rowvar=False)
    np.fill_diagonal(corr, 0.0)
    corr = np.nan_to_num(corr, nan=0.0)
    max_corr = float(np.nanmax(np.abs(corr)))
    assert max_corr < 0.999, f"near-duplicate columns found, max |corr|={max_corr}"


def test_volatilidade_varies_across_distant_idx(draws):
    """Regression test for F-04: distant idx values must produce different volatility."""
    v_low = volatilidade_score(draws, 100)
    v_high = volatilidade_score(draws, 240)
    assert v_low != v_high


@pytest.mark.parametrize("scorer", [coocorrencia_score, volatilidade_score, trend_score])
def test_no_temporal_leakage(draws, scorer):
    """Mutating a draw strictly after idx must not change the score computed at idx."""
    idx = 150
    before = scorer(draws, idx)
    mutated = _with_mutated_draw(draws, idx + 10)
    after = scorer(mutated, idx)
    assert before == after


def test_coocorrencia_lift_near_one_under_independence(draws):
    """
    Regression test for two code-review fixes: (a) the "no evidence" case
    returning the neutral 1.0 instead of 0.0, and (b) alpha=1.0 additive
    smoothing. With truly independent (uniformly random) draws, the score
    averaged across numbers and idx values must land close to -- but per the
    HONEST NOTE in coocorrencia_score, not exactly at -- 1.0.

    Dia de Sorte is moderately sparse (esperado(n, m) ~1.5 in a 30-draw
    window). Measured on this fixture's seed, the current code gives a
    grand mean of ~0.932 (|dev|~0.068). The residual bias is Jensen's-
    inequality shrinkage, documented in the docstring, not a bug -- but the
    tolerance below is tight enough that regressing either fix (or losing
    the fix in a refactor) makes this test fail.
    """
    means = []
    for idx in range(30, N_DRAWS):
        scores = coocorrencia_score(draws, idx, k=30, top=10)
        vals = list(scores.values())
        means.append(sum(vals) / len(vals))
    grand_mean = sum(means) / len(means)
    assert abs(grand_mean - 1.0) < 0.10, f"grand mean lift={grand_mean}, too far from 1.0"
