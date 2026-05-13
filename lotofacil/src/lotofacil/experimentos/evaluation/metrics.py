"""Evaluation metrics for walk-forward results."""

from __future__ import annotations

import math
from collections import Counter
from typing import Dict, List

import numpy as np

from lotofacil.experimentos.config import COST_PER_GAME, PRIZE_TABLE


def mean_hits(results: List[dict]) -> float:
    if not results:
        return 0.0
    return sum(r["hits"] for r in results) / len(results)


def hits_distribution(results: List[dict]) -> Dict[int, int]:
    return dict(Counter(r["hits"] for r in results))


def rate_ge(results: List[dict], threshold: int) -> float:
    if not results:
        return 0.0
    return sum(1 for r in results if r["hits"] >= threshold) / len(results)


def financial_metrics(results: List[dict]) -> dict:
    """Compute ROI, Sharpe, MaxDD, equity curve from walk-forward results."""
    n = len(results)
    if n == 0:
        return {}

    equity = 0.0
    equity_curve = []
    returns = []
    hits_dist: Dict[int, int] = {}

    for r in results:
        hits = r.get("hits", 0)
        hits_dist[hits] = hits_dist.get(hits, 0) + 1
        prize = PRIZE_TABLE.get(hits, 0.0)
        net = prize - COST_PER_GAME
        equity += net
        equity_curve.append(equity)
        returns.append(net)

    total_cost = n * COST_PER_GAME
    total_revenue = sum(PRIZE_TABLE.get(r.get("hits", 0), 0.0) for r in results)
    net_profit = total_revenue - total_cost
    roi_pct = (net_profit / total_cost * 100) if total_cost > 0 else 0.0

    # Max drawdown
    peak = equity_curve[0]
    max_dd = 0.0
    for v in equity_curve:
        peak = max(peak, v)
        max_dd = min(max_dd, v - peak)

    # Sharpe (simplified: mean / std of per-game net returns)
    mean_r = sum(returns) / len(returns)
    variance = sum((r - mean_r) ** 2 for r in returns) / max(len(returns) - 1, 1)
    std_r = math.sqrt(variance) if variance > 0 else 0.0
    sharpe = (mean_r / std_r) if std_r > 0 else 0.0

    return {
        "n_games": n,
        "total_cost": round(total_cost, 2),
        "total_revenue": round(total_revenue, 2),
        "net_profit": round(net_profit, 2),
        "roi_pct": round(roi_pct, 2),
        "max_drawdown": round(max_dd, 2),
        "sharpe": round(sharpe, 4),
        "mean_hits": round(mean_hits(results), 4),
        "hits_distribution": hits_dist,
        "rate_ge_11": round(rate_ge(results, 11), 4),
        "rate_ge_12": round(rate_ge(results, 12), 4),
        "rate_ge_13": round(rate_ge(results, 13), 4),
        "equity_curve": equity_curve,
    }


def vs_random_p_value(model_hits: List[int], n_numbers: int = 25, n_draw: int = 15) -> float:
    """One-sided p-value: is model's mean hits > random expectation?

    Under null, each game is independent Hypergeometric(25, 15, 15).
    Expected hits = 15*15/25 = 9.0. Uses normal approximation.
    """
    if not model_hits:
        return 1.0
    mu = n_draw * n_draw / n_numbers          # 9.0
    var = mu * (n_numbers - n_draw) / n_numbers * (n_numbers - n_draw) / (n_numbers - 1)
    std = math.sqrt(var / len(model_hits))    # std of sample mean
    z = (sum(model_hits) / len(model_hits) - mu) / std if std > 0 else 0.0
    # one-sided p-value using normal CDF approximation
    p = 0.5 * math.erfc(z / math.sqrt(2))
    return round(p, 6)
