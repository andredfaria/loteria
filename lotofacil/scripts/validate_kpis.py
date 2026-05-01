"""Comprehensive KPI validation for 15-number neural model.

Proves statistical significance that the model beats random chance.
Validates against multiple baselines using walk-forward backtest.

Outputs: Terminal tables + JSON file with all metrics.
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import numpy as np
from scipy import stats
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.rule import Rule

from core.models import Draw
from core.config import TOTAL_NUMBERS, NUMBERS_PER_DRAW, COST_PER_GAME, PRIZE_TABLE, RANDOM_SEED
from core.lottery import contar_acertos, estatisticas_dezenas
from data.loader import load_draws

console = Console()

# ── Hypergeometric baseline ───────────────────────────────────────────────────

def hypergeometric_prob(k: int, drawn: int = 15, population: int = 25, sample: int = 15) -> float:
    """P(X=k) for hypergeometric: choose k from drawn, rest from non-drawn."""
    from math import comb
    if k < 0 or k > drawn or (sample - k) > (population - drawn) or (sample - k) < 0:
        return 0.0
    return comb(drawn, k) * comb(population - drawn, sample - k) / comb(population, sample)


def hypergeometric_cdf_ge(k: int, **kwargs) -> float:
    """P(X >= k) for hypergeometric (random 15-number bet)."""
    return sum(hypergeometric_prob(i, **kwargs) for i in range(k, 16))


def random_baseline_stats(n_sims: int = 100000, n_draws: int = 200) -> dict:
    """Monte Carlo simulation of random 15-number bets."""
    rng = np.random.RandomState(RANDOM_SEED)
    all_hits = []
    for _ in range(n_sims):
        bet = set(rng.choice(range(1, 26), size=15, replace=False))
        actual = set(rng.choice(range(1, 26), size=15, replace=False))
        all_hits.append(len(bet & actual))

    all_hits = np.array(all_hits)
    return {
        "mean_hits": float(np.mean(all_hits)),
        "median_hits": float(np.median(all_hits)),
        "std_hits": float(np.std(all_hits)),
        "hit_11_plus": float(np.mean(all_hits >= 11)),
        "hit_12_plus": float(np.mean(all_hits >= 12)),
        "hit_13_plus": float(np.mean(all_hits >= 13)),
        "hit_14_plus": float(np.mean(all_hits >= 14)),
        "hit_15": float(np.mean(all_hits == 15)),
        "best_hit": int(np.max(all_hits)),
        "worst_hit": int(np.min(all_hits)),
        "n_sims": n_sims,
    }


# ── Walk-forward runner ───────────────────────────────────────────────────────

def run_walkforward(draws: list[Draw], test_window: int, filtered: bool,
                     loaded: bool = False, use_ensemble: bool = False) -> list[dict]:
    """Run walk-forward and return per-draw results."""
    results = []
    n = len(draws)
    start = n - test_window - 300

    if loaded and not use_ensemble:
        from strategies.quinze_numbers.approaches.neural import NeuralApproach
        model = NeuralApproach()
        model.load()
    elif loaded and use_ensemble:
        from strategies.quinze_numbers.approaches.ensemble import EnsembleApproach
        model = EnsembleApproach()
        model.load()
    else:
        model = None

    for i in range(test_window):
        idx = start + i + 300
        train_draws = draws[idx - 300:idx]
        actual_draw = draws[idx]

        try:
            if loaded:
                if filtered:
                    top15 = model.predict_with_filters(train_draws)
                else:
                    probas = model.predict_proba(train_draws)
                    top15 = sorted(np.argsort(probas)[::-1][:15] + 1)
            else:
                if use_ensemble:
                    from strategies.quinze_numbers.approaches.ensemble import EnsembleApproach
                    model = EnsembleApproach()
                else:
                    from strategies.quinze_numbers.approaches.neural import NeuralApproach
                    model = NeuralApproach()
                model.fit(train_draws)
                if filtered:
                    top15 = model.predict_with_filters(train_draws)
                else:
                    probas = model.predict_proba()
                    top15 = sorted(np.argsort(probas)[::-1][:15] + 1)

            hits = contar_acertos(top15, actual_draw.dezenas)
            results.append({
                "concurso": actual_draw.concurso,
                "hits": hits,
                "predicted": top15,
                "actual": list(actual_draw.dezenas),
            })
        except Exception as e:
            console.print(f"  [yellow]Failed concurso {actual_draw.concurso}: {e}[/yellow]")

    return results


# ── KPI Calculator ────────────────────────────────────────────────────────────

class KPIReport:
    """Compute and display all KPIs for model validation."""

    def __init__(self, results: list[dict], label: str = "Model"):
        self.results = results
        self.label = label
        self.hits = np.array([r["hits"] for r in results])
        self.n = len(self.hits)

    def compute_all(self) -> dict:
        kpis = {}
        kpis["label"] = self.label
        kpis["n_draws"] = self.n
        kpis.update(self._basic_metrics())
        kpis.update(self._hit_rates())
        kpis.update(self._statistical_significance())
        kpis.update(self._financial_metrics())
        kpis.update(self._consistency_metrics())
        kpis.update(self._distribution_analysis())
        kpis.update(self._pattern_analysis())
        return kpis

    def _basic_metrics(self) -> dict:
        return {
            "mean_hits": float(np.mean(self.hits)),
            "median_hits": float(np.median(self.hits)),
            "std_hits": float(np.std(self.hits)),
            "best_hit": int(np.max(self.hits)),
            "worst_hit": int(np.min(self.hits)),
            "range": int(np.max(self.hits) - np.min(self.hits)),
        }

    def _hit_rates(self) -> dict:
        return {
            "hit_rate_11": float(np.mean(self.hits >= 11)),
            "hit_rate_12": float(np.mean(self.hits >= 12)),
            "hit_rate_13": float(np.mean(self.hits >= 13)),
            "hit_rate_14": float(np.mean(self.hits >= 14)),
            "hit_rate_15": float(np.mean(self.hits == 15)),
            "count_11_plus": int(np.sum(self.hits >= 11)),
            "count_12_plus": int(np.sum(self.hits >= 12)),
            "count_13_plus": int(np.sum(self.hits >= 13)),
        }

    def _statistical_significance(self) -> dict:
        p_random_11 = hypergeometric_cdf_ge(11)
        observed_11 = int(np.sum(self.hits >= 11))

        bt = stats.binomtest(observed_11, self.n, p_random_11, alternative='greater')
        binom_pvalue = bt.pvalue

        expected_under_null = self.n * p_random_11
        z_score = (observed_11 - expected_under_null) / np.sqrt(self.n * p_random_11 * (1 - p_random_11))

        hits_mean = np.mean(self.hits)
        random_mean = 9.0
        hits_std = np.std(self.hits)
        t_stat = (hits_mean - random_mean) / (hits_std / np.sqrt(self.n)) if hits_std > 0 else 0
        t_pvalue = stats.t.sf(t_stat, df=self.n - 1)

        ci_low, ci_high = stats.t.interval(0.95, self.n - 1,
                                            loc=np.mean(self.hits),
                                            scale=stats.sem(self.hits))

        cohens_d = (hits_mean - random_mean) / hits_std if hits_std > 0 else 0

        effect_label = "negligible"
        if abs(cohens_d) >= 0.8:
            effect_label = "large"
        elif abs(cohens_d) >= 0.5:
            effect_label = "medium"
        elif abs(cohens_d) >= 0.2:
            effect_label = "small"

        return {
            "random_p_11_plus": p_random_11,
            "random_expected_11_plus": round(expected_under_null, 1),
            "observed_11_plus": observed_11,
            "binomial_p_value": float(binom_pvalue),
            "binomial_significant_005": bool(binom_pvalue < 0.05),
            "binomial_significant_001": bool(binom_pvalue < 0.01),
            "z_score_11_plus": float(z_score),
            "t_stat_mean": float(t_stat),
            "t_pvalue_mean": float(t_pvalue),
            "mean_95_ci_low": round(float(ci_low), 3),
            "mean_95_ci_high": round(float(ci_high), 3),
            "cohens_d": round(float(cohens_d), 3),
            "effect_size": effect_label,
        }

    def _financial_metrics(self) -> dict:
        total_cost = self.n * COST_PER_GAME
        total_prize = sum(PRIZE_TABLE.get(int(h), 0) for h in self.hits)
        roi = (total_prize - total_cost) / total_cost * 100 if total_cost > 0 else 0

        per_game_returns = [(PRIZE_TABLE.get(int(h), 0) - COST_PER_GAME) for h in self.hits]
        sharpe = np.mean(per_game_returns) / np.std(per_game_returns) if np.std(per_game_returns) > 0 else 0

        cumulative = np.cumsum(per_game_returns)
        peak = np.maximum.accumulate(cumulative)
        drawdowns = peak - cumulative
        max_drawdown = float(np.max(drawdowns))
        calmar = roi / max_drawdown if max_drawdown > 0 else 0

        wins = sum(1 for r in per_game_returns if r > 0)
        win_rate = wins / self.n if self.n > 0 else 0

        return {
            "total_cost": total_cost,
            "total_prize": total_prize,
            "net_profit": total_prize - total_cost,
            "roi_percent": round(roi, 2),
            "sharpe_ratio": round(sharpe, 3),
            "max_drawdown": round(max_drawdown, 2),
            "calmar_ratio": round(calmar, 3),
            "win_rate": round(win_rate, 4),
        }

    def _consistency_metrics(self) -> dict:
        sorted_hits = np.sort(self.hits)
        streaks = []
        current_streak = 0
        for h in self.hits:
            if h >= 11:
                current_streak += 1
            else:
                if current_streak > 0:
                    streaks.append(current_streak)
                current_streak = 0
        if current_streak > 0:
            streaks.append(current_streak)

        loss_streaks = []
        current_loss = 0
        for h in self.hits:
            if h < 11:
                current_loss += 1
            else:
                if current_loss > 0:
                    loss_streaks.append(current_loss)
                current_loss = 0
        if current_loss > 0:
            loss_streaks.append(current_loss)

        return {
            "std_hits": float(np.std(self.hits)),
            "cv_hits": round(float(np.std(self.hits) / np.mean(self.hits)), 4) if np.mean(self.hits) > 0 else 0,
            "iqr": float(np.percentile(self.hits, 75) - np.percentile(self.hits, 25)),
            "max_win_streak": max(streaks) if streaks else 0,
            "avg_win_streak": round(float(np.mean(streaks)), 2) if streaks else 0,
            "max_loss_streak": max(loss_streaks) if loss_streaks else 0,
            "avg_loss_streak": round(float(np.mean(loss_streaks)), 2) if loss_streaks else 0,
        }

    def _distribution_analysis(self) -> dict:
        dist = {}
        for h in sorted(set(self.hits)):
            dist[int(h)] = int(np.sum(self.hits == h))

        all_numbers_predicted = []
        for r in self.results:
            all_numbers_predicted.extend(r["predicted"])

        freq_counts = np.zeros(25)
        for n in all_numbers_predicted:
            freq_counts[n - 1] += 1

        chi2_stat, chi2_p = stats.chisquare(freq_counts)

        return {
            "hits_distribution": dist,
            "number_coverage_chi2": round(float(chi2_stat), 2),
            "number_coverage_p_value": round(float(chi2_p), 4),
            "number_coverage_uniform": bool(chi2_p > 0.05),
            "most_predicted": [int(i + 1) for i in np.argsort(freq_counts)[::-1][:5]],
            "least_predicted": [int(i + 1) for i in np.argsort(freq_counts)[:5]],
        }

    def _pattern_analysis(self) -> dict:
        pattern_stats = []
        for r in self.results:
            s = estatisticas_dezenas(r["predicted"])
            pattern_stats.append(s)

        return {
            "avg_soma": round(float(np.mean([s["soma"] for s in pattern_stats])), 1),
            "avg_pares": round(float(np.mean([s["pares"] for s in pattern_stats])), 1),
            "avg_primos": round(float(np.mean([s["primos"] for s in pattern_stats])), 1),
            "avg_fibonacci": round(float(np.mean([s["fibonacci"] for s in pattern_stats])), 1),
            "avg_moldura": round(float(np.mean([s["moldura"] for s in pattern_stats])), 1),
            "avg_consecutivos": round(float(np.mean([s["consecutivos"] for s in pattern_stats])), 1),
        }


# ── Display ───────────────────────────────────────────────────────────────────

def display_kpis(kpis: dict):
    """Display KPIs in formatted terminal tables."""
    console.print(Rule(f"[bold cyan]{kpis['label']} — KPI Report[/bold cyan]"))

    t1 = Table(title="1. Basic Metrics")
    t1.add_column("Metric", style="cyan")
    t1.add_column("Value", style="green", justify="right")
    t1.add_row("Draws Tested", str(kpis["n_draws"]))
    t1.add_row("Mean Hits", f"{kpis['mean_hits']:.3f}")
    t1.add_row("Median Hits", f"{kpis['median_hits']:.1f}")
    t1.add_row("Std Dev", f"{kpis['std_hits']:.3f}")
    t1.add_row("Best / Worst", f"{kpis['best_hit']} / {kpis['worst_hit']}")
    console.print(t1)

    t2 = Table(title="2. Hit Rates")
    t2.add_column("Threshold", style="cyan")
    t2.add_column("Count", style="green", justify="right")
    t2.add_column("Rate", style="green", justify="right")
    for threshold in [11, 12, 13, 14, 15]:
        count = kpis[f"count_{threshold}_plus"] if threshold < 15 else kpis.get("hit_15", 0)
        rate = kpis[f"hit_rate_{threshold}"]
        t2.add_row(f">= {threshold}", str(count), f"{rate * 100:.1f}%")
    console.print(t2)

    sig = kpis
    t3 = Table(title="3. Statistical Significance (vs Random)")
    t3.add_column("Test", style="cyan")
    t3.add_column("Value", style="green", justify="right")
    t3.add_row("Random P(11+)", f"{sig['random_p_11_plus'] * 100:.2f}%")
    t3.add_row("Expected 11+ (null)", str(sig["random_expected_11_plus"]))
    t3.add_row("Observed 11+", str(sig["observed_11_plus"]))
    t3.add_row("Binomial p-value", f"{sig['binomial_p_value']:.6f}")

    sig_label = ""
    if sig["binomial_significant_001"]:
        sig_label = "*** p<0.01"
    elif sig["binomial_significant_005"]:
        sig_label = "** p<0.05"
    else:
        sig_label = "n.s."
    t3.add_row("Significance", sig_label)
    t3.add_row("Z-score", f"{sig['z_score_11_plus']:.3f}")
    t3.add_row("Cohen's d", f"{sig['cohens_d']:.3f} ({sig['effect_size']})")
    t3.add_row("95% CI Mean", f"[{sig['mean_95_ci_low']}, {sig['mean_95_ci_high']}]")
    console.print(t3)

    t4 = Table(title="4. Financial Metrics")
    t4.add_column("Metric", style="cyan")
    t4.add_column("Value", style="green", justify="right")
    t4.add_row("Total Cost", f"R$ {kpis['total_cost']:.2f}")
    t4.add_row("Total Prize", f"R$ {kpis['total_prize']:.2f}")
    t4.add_row("Net Profit", f"R$ {kpis['net_profit']:.2f}")
    t4.add_row("ROI", f"{kpis['roi_percent']:.2f}%")
    t4.add_row("Sharpe Ratio", f"{kpis['sharpe_ratio']:.3f}")
    t4.add_row("Max Drawdown", f"R$ {kpis['max_drawdown']:.2f}")
    t4.add_row("Calmar Ratio", f"{kpis['calmar_ratio']:.3f}")
    t4.add_row("Win Rate", f"{kpis['win_rate'] * 100:.1f}%")
    console.print(t4)

    t5 = Table(title="5. Consistency")
    t5.add_column("Metric", style="cyan")
    t5.add_column("Value", style="green", justify="right")
    t5.add_row("Std Dev", f"{kpis['std_hits']:.3f}")
    t5.add_row("CV", f"{kpis['cv_hits']:.4f}")
    t5.add_row("IQR", f"{kpis['iqr']:.1f}")
    t5.add_row("Max Win Streak", str(kpis["max_win_streak"]))
    t5.add_row("Avg Win Streak", str(kpis["avg_win_streak"]))
    t5.add_row("Max Loss Streak", str(kpis["max_loss_streak"]))
    t5.add_row("Avg Loss Streak", str(kpis["avg_loss_streak"]))
    console.print(t5)

    t6 = Table(title="6. Pattern Analysis (Avg)")
    t6.add_column("Pattern", style="cyan")
    t6.add_column("Avg", style="green", justify="right")
    t6.add_row("Soma", f"{kpis['avg_soma']:.1f}")
    t6.add_row("Pares", f"{kpis['avg_pares']:.1f}")
    t6.add_row("Primos", f"{kpis['avg_primos']:.1f}")
    t6.add_row("Fibonacci", f"{kpis['avg_fibonacci']:.1f}")
    t6.add_row("Moldura", f"{kpis['avg_moldura']:.1f}")
    t6.add_row("Consecutivos", f"{kpis['avg_consecutivos']:.1f}")
    console.print(t6)

    veredict = ""
    if sig["binomial_significant_001"]:
        veredict = "[bold green]SIGNIFICANT (p<0.01) — Model is NOT random[/bold green]"
    elif sig["binomial_significant_005"]:
        veredict = "[bold yellow]MARGINALLY SIGNIFICANT (p<0.05) — Weak evidence[/bold yellow]"
    else:
        veredict = "[bold red]NOT SIGNIFICANT — Could be random chance[/bold red]"
    console.print(Panel(veredict, title="Veredict"))


def display_comparison(pure: dict, filtered: dict, random: dict):
    """Side-by-side comparison of all three."""
    t = Table(title="Model Comparison: Pure vs Filtered vs Random")
    t.add_column("Metric", style="cyan")
    t.add_column("Pure Neural", style="green", justify="right")
    t.add_column("Neural + Filters", style="green", justify="right")
    t.add_column("Random", style="dim", justify="right")

    metrics = [
        ("Mean Hits", "mean_hits", "mean_hits", "mean_hits"),
        ("Std Dev", "std_hits", "std_hits", "std_hits"),
        ("Hit Rate 11+", "hit_rate_11", "hit_rate_11", "hit_11_plus"),
        ("Hit Rate 12+", "hit_rate_12", "hit_rate_12", "hit_12_plus"),
        ("Hit Rate 13+", "hit_rate_13", "hit_rate_13", "hit_13_plus"),
        ("Best Hit", "best_hit", "best_hit", "best_hit"),
        ("Worst Hit", "worst_hit", "worst_hit", "worst_hit"),
        ("Binomial p-value", "binomial_p_value", "binomial_p_value", "—"),
        ("Effect Size (d)", "cohens_d", "cohens_d", "—"),
        ("ROI %", "roi_percent", "roi_percent", "—"),
        ("Sharpe", "sharpe_ratio", "sharpe_ratio", "—"),
        ("Max Loss Streak", "max_loss_streak", "max_loss_streak", "—"),
    ]

    for label, pk, fk, rk in metrics:
        pv = f"{pure[pk]:.3f}" if isinstance(pure[pk], float) else str(pure[pk])
        fv = f"{filtered[fk]:.3f}" if isinstance(filtered[fk], float) else str(filtered[fk])
        rv = "—" if rk == "—" else (f"{random[rk]:.4f}" if isinstance(random.get(rk), float) else str(random.get(rk, "—")))
        t.add_row(label, pv, fv, rv)

    console.print(t)


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="KPI validation for 15-number neural model")
    parser.add_argument("--window", "-w", type=int, default=200, help="Test window size (default: 200)")
    parser.add_argument("--train", "-t", type=int, default=300, help="Training window (default: 300)")
    parser.add_argument("--loaded", "-l", action="store_true", help="Use pre-trained model")
    parser.add_argument("--ensemble", "-e", action="store_true", help="Use ensemble (Neural + Frequency)")
    parser.add_argument("--output", "-o", type=str, default="output/kpi_report.json", help="Output JSON path")
    args = parser.parse_args()

    draws = load_draws(source="db")
    n = len(draws)
    required = args.train + args.window

    if n < required:
        console.print(f"[red]Need {required} draws, got {n}[/red]")
        sys.exit(1)

    model_label = "Ensemble (Neural+Freq)" if args.ensemble else "Neural"
    console.print(f"[bold]KPI Validation — 15-Number {model_label} Model[/bold]")
    console.print(f"Total draws available: {n}")
    console.print(f"Test window: {args.window} draws")
    console.print(f"Training window: {args.train} draws")
    console.print()

    console.print(f"[bold cyan]Phase 1: Random baseline (Monte Carlo, 100k sims)[/bold cyan]")
    random_stats = random_baseline_stats(n_sims=100000)
    console.print(f"  Random mean hits: {random_stats['mean_hits']:.2f}")
    console.print(f"  Random P(11+): {random_stats['hit_11_plus'] * 100:.2f}%")
    console.print()

    # Run pure model
    console.print(f"[bold cyan]Phase 2: {model_label} walk-forward (pure)[/bold cyan]")
    t0 = time.time()
    pure_results = run_walkforward(draws, args.window, filtered=False, loaded=args.loaded,
                                    use_ensemble=args.ensemble)
    t_pure = time.time() - t0
    console.print(f"  Done in {t_pure:.1f}s — {len(pure_results)} results")

    # Run filtered model
    console.print(f"[bold cyan]Phase 3: {model_label} + filters walk-forward[/bold cyan]")
    t0 = time.time()
    filtered_results = run_walkforward(draws, args.window, filtered=True, loaded=args.loaded,
                                        use_ensemble=args.ensemble)
    t_filtered = time.time() - t0
    console.print(f"  Done in {t_filtered:.1f}s — {len(filtered_results)} results")
    console.print()

    console.print("[bold cyan]Computing KPIs...[/bold cyan]")
    pure_kpi = KPIReport(pure_results, "Pure Neural").compute_all()
    filtered_kpi = KPIReport(filtered_results, "Neural + Filters").compute_all()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    report = {
        "timestamp": datetime.now().isoformat(),
        "test_window": args.window,
        "train_window": args.train,
        "n_total_draws": n,
        "random_baseline": random_stats,
        "pure_neural": pure_kpi,
        "neural_filtered": filtered_kpi,
    }

    with open(output_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    console.print(f"\n[dim]Full report saved to {output_path}[/dim]")
    console.print()

    display_comparison(pure_kpi, filtered_kpi, random_stats)
    console.print()
    display_kpis(filtered_kpi)
