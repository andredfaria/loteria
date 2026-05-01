"""Statistical significance testing: model vs baseline."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List


@dataclass
class SignificanceResult:
    model_mean: float
    baseline_mean: float
    improvement_pct: float
    p_value: float
    test_used: str
    significant: bool
    interpretation: str


def _ttest_paired(a: List[float], b: List[float]) -> float:
    """Paired t-test p-value (two-tailed). Returns p-value."""
    n = len(a)
    if n < 2:
        return 1.0
    diffs = [x - y for x, y in zip(a, b)]
    mean_d = sum(diffs) / n
    var_d = sum((d - mean_d) ** 2 for d in diffs) / (n - 1)
    if var_d == 0:
        return 1.0
    se = math.sqrt(var_d / n)
    t = mean_d / se
    # Approximate two-tailed p-value using normal approximation for large n
    # For n >= 30, t ≈ z
    z = abs(t)
    p = _normal_sf(z) * 2
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


def _mannwhitney_u(a: List[float], b: List[float]) -> float:
    """Mann-Whitney U test p-value approximation."""
    na, nb = len(a), len(b)
    if na == 0 or nb == 0:
        return 1.0
    u = 0
    for xi in a:
        for xj in b:
            if xi > xj:
                u += 1
            elif xi == xj:
                u += 0.5
    mean_u = na * nb / 2
    std_u = math.sqrt(na * nb * (na + nb + 1) / 12)
    if std_u == 0:
        return 1.0
    z = abs(u - mean_u) / std_u
    return min(1.0, _normal_sf(z) * 2)


def compare_vs_baseline(
    model_hits: List[int],
    baseline_hits: List[int],
    alpha: float = 0.05,
) -> SignificanceResult:
    """
    Compare model hit counts vs baseline hit counts.

    Uses paired t-test when n >= 30, Mann-Whitney U otherwise.
    Both lists must have the same length (paired per concurso).
    """
    n = min(len(model_hits), len(baseline_hits))
    if n == 0:
        return SignificanceResult(0, 0, 0, 1.0, "none", False, "Insufficient data")

    a = [float(x) for x in model_hits[:n]]
    b = [float(x) for x in baseline_hits[:n]]

    model_mean = sum(a) / n
    baseline_mean = sum(b) / n
    improvement = ((model_mean - baseline_mean) / baseline_mean * 100) if baseline_mean > 0 else 0.0

    if n >= 30:
        p = _ttest_paired(a, b)
        test_used = "paired t-test"
    else:
        p = _mannwhitney_u(a, b)
        test_used = "Mann-Whitney U"

    significant = p < alpha
    if significant and improvement > 0:
        interpretation = (
            f"Modelo superior ao baseline (p={p:.4f} < {alpha}). "
            f"Ganho médio: +{improvement:.2f}% acertos."
        )
    elif significant and improvement < 0:
        interpretation = (
            f"Modelo inferior ao baseline (p={p:.4f} < {alpha}). "
            f"Perda média: {improvement:.2f}% acertos."
        )
    else:
        interpretation = (
            f"Sem evidência estatística de diferença (p={p:.4f} >= {alpha}). "
            "O modelo não supera o baseline de forma robusta."
        )

    return SignificanceResult(
        model_mean=model_mean,
        baseline_mean=baseline_mean,
        improvement_pct=improvement,
        p_value=p,
        test_used=test_used,
        significant=significant,
        interpretation=interpretation,
    )
