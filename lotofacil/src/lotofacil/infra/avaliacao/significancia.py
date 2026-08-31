"""Statistical significance testing: model vs baseline."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional

try:  # SciPy chega junto com scikit-learn; o fallback existe para instalacoes minimas.
    from scipy import stats as _scipy_stats
except ImportError:  # pragma: no cover
    _scipy_stats = None


@dataclass
class SignificanceResult:
    model_mean: float
    baseline_mean: float
    improvement_pct: float
    p_value: float
    test_used: str
    significant: bool
    status: str
    statistical_confidence: str
    interpretation: str


def _ttest_paired(a: List[float], b: List[float]) -> Optional[float]:
    """Paired t-test p-value (two-tailed), or None if SciPy is unavailable.

    The p-value MUST come from Student's t with n-1 degrees of freedom. An
    earlier version of this function evaluated the t statistic against the
    standard normal instead, which underestimates the p-value systematically —
    always in the direction of declaring significance too early. At n=30 the
    reported p was 0.0408 where the correct value is 0.0500 (18% low), enough
    to flip a borderline result into "the model beats random".

    In a lottery project a false positive of significance is the worst possible
    output: it is exactly the "my model beats chance" claim the disclaimers
    exist to prevent. So when SciPy is missing we return None and let the
    caller fall back to a test we can compute exactly, rather than reporting a
    number we know to be biased.
    """
    if _scipy_stats is None:
        return None
    n = len(a)
    if n < 2:
        return 1.0
    diffs = [x - y for x, y in zip(a, b)]
    if all(d == diffs[0] for d in diffs):
        # Zero variance: the t statistic is undefined (or infinite).
        return 1.0
    p = float(_scipy_stats.ttest_rel(a, b).pvalue)
    if not math.isfinite(p):
        return 1.0
    return min(1.0, max(0.0, p))


def _normal_sf(z: float) -> float:
    """Survival function P(Z > z) for standard normal (Abramowitz & Stegun approx)."""
    if z < 0:
        return 1.0 - _normal_sf(-z)
    t = 1.0 / (1.0 + 0.2316419 * z)
    poly = t * (0.319381530
                + t * (-0.356563782
                       + t * (1.781477937
                              + t * (-1.821255978
                                     + t * 1.330274429))))
    return poly * math.exp(-0.5 * z * z) / math.sqrt(2 * math.pi)


def _binom_two_sided_pvalue(successes: int, n: int) -> float:
    """Exact two-sided binomial p-value with p0=0.5."""
    if n <= 0:
        return 1.0
    tail = min(successes, n - successes)
    cdf = sum(math.comb(n, k) for k in range(0, tail + 1)) / (2 ** n)
    return min(1.0, 2.0 * cdf)


def _wilcoxon_signed_rank(a: List[float], b: List[float]) -> tuple[float, str]:
    """Wilcoxon signed-rank test (normal approximation) with robust fallback."""
    diffs = [x - y for x, y in zip(a, b)]
    non_zero_diffs = [d for d in diffs if d != 0]
    n = len(non_zero_diffs)
    if n < 2:
        return 1.0, "fallback (all ties or n<2)"

    abs_with_sign = sorted((abs(d), 1 if d > 0 else -1) for d in non_zero_diffs)

    ranks_with_sign = []
    i = 0
    rank = 1
    while i < n:
        j = i
        while j + 1 < n and abs_with_sign[j + 1][0] == abs_with_sign[i][0]:
            j += 1
        avg_rank = (rank + rank + (j - i)) / 2
        for k in range(i, j + 1):
            ranks_with_sign.append((avg_rank, abs_with_sign[k][1]))
        rank += (j - i + 1)
        i = j + 1

    w_plus = sum(r for r, s in ranks_with_sign if s > 0)
    mean_w = n * (n + 1) / 4
    var_w = n * (n + 1) * (2 * n + 1) / 24
    if var_w == 0:
        # Extreme/tied scenario: fallback to paired sign test
        positive = sum(1 for d in non_zero_diffs if d > 0)
        return _binom_two_sided_pvalue(positive, n), "fallback (paired sign test)"

    z = abs((w_plus - mean_w) / math.sqrt(var_w))
    p = min(1.0, _normal_sf(z) * 2)

    if not math.isfinite(p):
        positive = sum(1 for d in non_zero_diffs if d > 0)
        return _binom_two_sided_pvalue(positive, n), "fallback (paired sign test)"

    return p, "wilcoxon signed-rank"


def compare_vs_baseline(
    model_hits: List[int],
    baseline_hits: List[int],
    alpha: float = 0.05,
) -> SignificanceResult:
    """Compare paired model hit counts vs baseline hit counts."""
    n = min(len(model_hits), len(baseline_hits))
    if n == 0:
        return SignificanceResult(0, 0, 0, 1.0, "none", False, "insufficient_data", "low", "Dados insuficientes para teste estatístico.")

    a = [float(x) for x in model_hits[:n]]
    b = [float(x) for x in baseline_hits[:n]]

    model_mean = sum(a) / n
    baseline_mean = sum(b) / n
    improvement = ((model_mean - baseline_mean) / baseline_mean * 100) if baseline_mean > 0 else 0.0

    if n >= 30:
        p_t = _ttest_paired(a, b)
        if p_t is not None:
            p, test_used = p_t, "paired t-test"
        else:
            # Sem SciPy nao ha como avaliar a distribuicao t corretamente.
            # Degradamos para um teste que sabemos calcular, e dizemos qual foi.
            p, wilcoxon_mode = _wilcoxon_signed_rank(a, b)
            test_used = f"Wilcoxon signed-rank ({wilcoxon_mode}; SciPy ausente)"
    else:
        p, wilcoxon_mode = _wilcoxon_signed_rank(a, b)
        test_used = f"Wilcoxon signed-rank ({wilcoxon_mode})"

    significant = p < alpha
    status = "significant" if significant else "not_significant"

    if n < 10:
        confidence = "low"
    elif n < 30:
        confidence = "medium"
    else:
        confidence = "high"

    hypothesis = "H0: mediana/média das diferenças pareadas = 0 (sem ganho do modelo)."
    low_n_note = " Limitação: amostra pequena reduz poder estatístico." if n < 30 else ""

    if significant and improvement > 0:
        verdict = f"Modelo superior ao baseline (p={p:.4f} < {alpha})."
    elif significant and improvement < 0:
        verdict = f"Modelo inferior ao baseline (p={p:.4f} < {alpha})."
    else:
        verdict = f"Sem evidência estatística de diferença (p={p:.4f} >= {alpha})."

    interpretation = (
        f"Teste utilizado: {test_used}. "
        f"Hipótese avaliada: {hypothesis} "
        f"{verdict} Ganho médio: {improvement:.2f}% acertos." 
        f"{low_n_note}"
    ).strip()

    return SignificanceResult(
        model_mean=model_mean,
        baseline_mean=baseline_mean,
        improvement_pct=improvement,
        p_value=p,
        test_used=test_used,
        significant=significant,
        status=status,
        statistical_confidence=confidence,
        interpretation=interpretation,
    )
