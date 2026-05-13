"""HTML report generator for backtest results."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, List

from jinja2 import Environment, FileSystemLoader

from lotofacil.infra.avaliacao.backtest import BacktestResult, BacktestSummary
from lotofacil.infra.avaliacao.financeiro import FinancialResult, FinancialSimulator
from lotofacil.infra.config import COST_PER_GAME, PRIZE_TABLE
from lotofacil.infra.avaliacao.significancia import SignificanceResult, compare_vs_baseline

_TEMPLATES_DIR = Path(__file__).parent / "templates"
_COLORS = ["#60a5fa", "#4ade80", "#f59e0b", "#f87171", "#a78bfa"]


def _round2(v: float) -> float:
    return round(v, 2)


class HTMLReportGenerator:
    def __init__(self, cost: float = COST_PER_GAME, prize_table: Dict[int, float] = None):
        self.cost = cost
        self.prizes = prize_table or dict(PRIZE_TABLE)
        self._env = Environment(loader=FileSystemLoader(str(_TEMPLATES_DIR)))

    def generate(
        self,
        summaries: Dict[str, BacktestSummary],
        baseline_results: list,
        output_path: Path,
    ) -> None:
        """
        Generate self-contained HTML report.

        Args:
            summaries: {model_name: BacktestSummary}
            baseline_results: random baseline objects with .hits and .concurso
            output_path: where to write the .html file
        """
        sim = FinancialSimulator(cost_per_game=self.cost, prize_table=self.prizes)
        baseline_hits = [r.hits for r in baseline_results]
        random_mean = sum(baseline_hits) / len(baseline_hits) if baseline_hits else 0.0

        all_concursos = sorted({r.concurso for summary in summaries.values() for r in summary.results})
        concurso_labels = [str(c) for c in all_concursos]

        model_data = []
        equity_datasets = []
        hits_datasets = []

        best_model = None
        best_mean = -1.0

        for i, (name, summary) in enumerate(summaries.items()):
            results_dicts = [{"hits": r.hits} for r in summary.results]
            fr: FinancialResult = sim.simulate(results_dicts)
            model_hits = [r.hits for r in summary.results]
            sig: SignificanceResult = compare_vs_baseline(model_hits, baseline_hits)

            color = _COLORS[i % len(_COLORS)]

            # Equity curve aligned to all_concursos
            concurso_to_idx = {c: j for j, c in enumerate(all_concursos)}
            equity_by_concurso = [None] * len(all_concursos)
            running = 0.0
            for r in summary.results:
                prize = self.prizes.get(r.hits, 0.0)
                running += prize - self.cost
                if r.concurso in concurso_to_idx:
                    equity_by_concurso[concurso_to_idx[r.concurso]] = _round2(running)

            equity_datasets.append({
                "label": name,
                "data": equity_by_concurso,
                "borderColor": color,
                "backgroundColor": "transparent",
                "tension": 0.3,
                "spanGaps": True,
            })

            # Hits distribution (11-15)
            dist = summary.hit_distribution
            hits_datasets.append({
                "label": name,
                "data": [dist.get(k, 0) for k in range(11, 16)],
                "backgroundColor": color + "99",
                "borderColor": color,
                "borderWidth": 1,
            })

            if summary.mean_hits > best_mean:
                best_mean = summary.mean_hits
                best_model = name

            model_data.append({
                "name": name,
                "mean_hits": _round2(summary.mean_hits),
                "rate_11": _round2(summary.rate_ge.get(11, 0.0) * 100),
                "rate_12": _round2(summary.rate_ge.get(12, 0.0) * 100),
                "roi": _round2(fr.roi_pct),
                "net_profit": _round2(fr.net_profit),
                "max_drawdown": _round2(fr.max_drawdown),
                "total_cost": _round2(fr.total_cost),
                "total_revenue": _round2(fr.total_revenue),
                "n_games": fr.n_games,
                "sharpe": _round2(fr.sharpe),
                "p_value": _round2(sig.p_value),
                "significant": sig.significant,
                "interpretation": sig.interpretation,
            })

        # Best model summary for header cards
        best = next((m for m in model_data if m["name"] == best_model), model_data[0] if model_data else {})

        # Alerts
        alerts = [
            "A Lotofácil é um sorteio independente. Resultados históricos não garantem desempenho futuro.",
            "O backtest é walk-forward (sem leakage), mas mesmo assim pode sofrer de overfitting in-sample.",
            "Prêmios fixos são estimativas. Valores reais variam por concurso.",
        ]
        if best.get("p_value", 1.0) > 0.05:
            alerts.append("Nenhum modelo mostrou vantagem estatisticamente significativa sobre o baseline aleatório.")

        # Conclusion
        if best.get("p_value", 1.0) < 0.05 and best.get("roi", -100) > -50:
            conclusion = (
                f"O modelo '{best_model}' apresentou desempenho estatisticamente superior ao baseline "
                f"(p={best.get('p_value')}, melhoria de {best.get('improvement_pct', 0):.1f}%). "
                "Ainda assim, o ROI é negativo — a vantagem não é suficiente para cobrir o custo por jogo. "
                "Não há evidência de estratégia lucrativa robusta."
            )
        else:
            conclusion = (
                "Nenhum dos modelos testados apresentou vantagem estatisticamente robusta sobre a seleção aleatória. "
                "O ROI é negativo para todos os modelos, como esperado dado o design da loteria. "
                "Este resultado é coerente com a teoria: sorteios são eventos independentes e não há padrão explorável."
            )

        start_c = all_concursos[0] if all_concursos else 0
        end_c = all_concursos[-1] if all_concursos else 0

        context = {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "start_concurso": start_c,
            "end_concurso": end_c,
            "n_concursos": len(all_concursos),
            "best_model": best_model or "N/A",
            "best_mean_hits": _round2(best_mean),
            "best_roi": best.get("roi", 0.0),
            "random_mean_hits": _round2(random_mean),
            "models": model_data,
            "concurso_labels": concurso_labels,
            "equity_datasets": equity_datasets,
            "hits_labels": ["11", "12", "13", "14", "15"],
            "hits_datasets": hits_datasets,
            "alerts": alerts,
            "conclusion": conclusion,
        }

        template = self._env.get_template("report.html")
        html = template.render(**context)

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html, encoding="utf-8")
