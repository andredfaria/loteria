"""Financial simulation for backtest results."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List

from lotofacil.infra.config import COST_PER_GAME, PRIZE_TABLE


@dataclass
class FinancialResult:
    n_games: int
    total_cost: float
    total_revenue: float
    net_profit: float
    roi_pct: float
    max_drawdown: float
    sharpe: float
    equity_curve: List[float]
    hits_distribution: Dict[int, int]
    rate_ge: Dict[int, float]


class FinancialSimulator:
    def __init__(
        self,
        cost_per_game: float = COST_PER_GAME,
        prize_table: Dict[int, float] = None,
    ):
        self.cost = cost_per_game
        self.prizes = prize_table if prize_table is not None else dict(PRIZE_TABLE)

    def simulate(self, results: List[dict]) -> FinancialResult:
        """
        Args:
            results: list of {"hits": int, ...}

        Returns:
            FinancialResult with all financial metrics.
        """
        n = len(results)
        if n == 0:
            return FinancialResult(0, 0, 0, 0, 0, 0, 0, [], {}, {})

        equity = 0.0
        equity_curve = []
        returns = []
        hits_dist = {k: 0 for k in range(16)}

        for r in results:
            hits = r.get("hits", 0)
            hits_dist[hits] = hits_dist.get(hits, 0) + 1
            prize = self.prizes.get(hits, 0.0)
            net = prize - self.cost
            equity += net
            equity_curve.append(equity)
            returns.append(net)

        total_cost = n * self.cost
        total_revenue = sum(self.prizes.get(r.get("hits", 0), 0.0) for r in results)
        net_profit = total_revenue - total_cost
        roi_pct = (net_profit / total_cost * 100) if total_cost > 0 else 0.0

        # Max drawdown
        peak = equity_curve[0]
        max_dd = 0.0
        for v in equity_curve:
            if v > peak:
                peak = v
            dd = v - peak
            if dd < max_dd:
                max_dd = dd

        # Sharpe (simplified: mean / std of per-game returns)
        mean_r = sum(returns) / len(returns)
        std_r = math.sqrt(sum((r - mean_r) ** 2 for r in returns) / len(returns)) if len(returns) > 1 else 0.0
        sharpe = (mean_r / std_r) if std_r > 0 else 0.0

        rate_ge = {t: sum(1 for r in results if r.get("hits", 0) >= t) / n for t in [11, 12, 13, 14, 15]}

        return FinancialResult(
            n_games=n,
            total_cost=total_cost,
            total_revenue=total_revenue,
            net_profit=net_profit,
            roi_pct=roi_pct,
            max_drawdown=max_dd,
            sharpe=sharpe,
            equity_curve=equity_curve,
            hits_distribution=hits_dist,
            rate_ge=rate_ge,
        )
