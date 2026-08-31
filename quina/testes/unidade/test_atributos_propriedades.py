"""
Property-based regression tests for infra.atributos.

Kept separate from test_atributos_base.py (which exercises base.py's simpler
functions in isolation) because these tests target two specific classes of
feature-engineering bugs found by inspection:

- F-04: a windowed feature (`volatilidade_score`) whose window did not track
  `idx`, so it froze into a constant once enough draws had accumulated.
  (Note: quina's own volatilidade_score already anchored its window on idx
  correctly -- megasena and dia-de-sorte had the bug -- but the property is
  tested here too so a future refactor can't silently reintroduce it.)
- F-05: a feature (`coocorrencia_score`) that was mathematically an affine
  rescaling of `freq_k`, providing zero information beyond it despite its
  name promising pairwise co-occurrence structure.

NOTE: `coocorrencia_score` and `volatilidade_score` are not currently wired
into quina's FeatureBuilder (see infra/atributos/builder.py, which only pulls
`faixa_dominante` and `par_quente_score` from advanced.py), so the dataset
produced by FeatureBuilder does not contain cooc_*/vol_* columns. The
constant-column and no-duplicate-column checks below run against the
functions directly instead of through the builder, so they still catch
regressions in code that today has no other consumer.

Draws are synthetic and generated from a seeded RNG for determinism.
"""

from __future__ import annotations

import random
from typing import List

import numpy as np
import pytest

from quina.dominio.entidades import Sorteio as Draw
from quina.infra.atributos.advanced import (
    coocorrencia_score,
    trend_score,
    volatilidade_score,
)
from quina.infra.atributos.base import freq_k
from quina.infra.atributos.builder import FeatureBuilder

TOTAL = 80
NUMEROS_POR_SORTEIO = 5
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


def test_no_constant_columns_in_builder_dataset(dataset):
    """
    Regression test for F-04, applied to columns the builder actually emits
    today (freq_*, atraso_*, soma_*, pares/impares_*, repeticao/consecutivos_*,
    std_frequencias, faixa_dominante, par_quente_score).
    """
    X, _, names = dataset
    stds = X.std(axis=0)
    constant = [names[i] for i in range(X.shape[1]) if stds[i] == 0]
    assert not constant, f"constant columns found: {constant}"


def test_no_near_duplicate_columns_in_builder_dataset(dataset):
    """
    Regression test for F-05, applied to columns the builder actually emits
    today.

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


def test_coocorrencia_not_aliased_to_freq(draws):
    """
    Direct regression test for F-05, since coocorrencia_score is not wired
    into the builder dataset: across idx values, coocorrencia_score(n) must
    not just be a rescaling of freq_k(n) for the same window/number.
    """
    idx = 150
    cooc = coocorrencia_score(draws, idx, k=50)
    freq = freq_k(draws, idx, 50)
    cooc_vals = np.array([cooc[n] for n in range(1, TOTAL + 1)])
    freq_vals = np.array([freq[n] for n in range(1, TOTAL + 1)])
    corr = np.corrcoef(cooc_vals, freq_vals)[0, 1]
    assert abs(corr) < 0.999, f"coocorrencia_score still aliases freq_k, corr={corr}"


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

    Quina is the sparsest of the four lotteries (esperado(n, m) << 1 with
    k=50, top=20). Measured on this fixture's seed: no-evidence-as-0.0
    without smoothing gave |dev|~0.21 (the worst of the four); either fix
    alone narrows it; both together (current code) gives a measured grand
    mean of ~0.957 (|dev|~0.043). The residual bias is Jensen's-inequality
    shrinkage, documented in the docstring, not a bug -- but the tolerance
    below is tight enough that regressing either fix (or losing the fix in
    a refactor) makes this test fail.
    """
    means = []
    for idx in range(50, N_DRAWS):
        scores = coocorrencia_score(draws, idx, k=50, top=20)
        vals = list(scores.values())
        means.append(sum(vals) / len(vals))
    grand_mean = sum(means) / len(means)
    assert abs(grand_mean - 1.0) < 0.08, f"grand mean lift={grand_mean}, too far from 1.0"
