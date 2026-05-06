"""Generate report artifacts from ExperimentRunner output."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import numpy as np

from lotofacil_lab.config import OUTPUT_DIR, COST_PER_GAME

logger = logging.getLogger(__name__)


def _check_matplotlib():
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        return plt
    except ImportError:
        logger.warning("matplotlib not available — skipping plots.")
        return None


def generate_report(experiment_result: dict, output_dir: Path | None = None) -> Path:
    """Generate all report artifacts in output_dir.

    Args:
        experiment_result: dict returned by ExperimentRunner.run()
        output_dir: Where to write artefacts. Defaults to OUTPUT_DIR/<timestamp>/.

    Returns:
        Path to the output directory.
    """
    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    out = (output_dir or OUTPUT_DIR) / ts
    out.mkdir(parents=True, exist_ok=True)

    # ── 1. Raw metrics JSON ───────────────────────────────────────────────────
    metrics_path = out / "metrics.json"
    # Remove equity_curve from JSON (too large) and raw_results
    slim = _slim_for_json(experiment_result)
    metrics_path.write_text(json.dumps(slim, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Written: %s", metrics_path)

    # ── 2. Markdown report ─────────────────────────────────────────────────────
    md_path = out / "report.md"
    md_path.write_text(_build_markdown(experiment_result), encoding="utf-8")
    logger.info("Written: %s", md_path)

    # ── 3. Plots ──────────────────────────────────────────────────────────────
    plt = _check_matplotlib()
    if plt:
        _plot_equity_curves(experiment_result["results"], out / "equity_curves.png", plt)
        _plot_hits_distribution(experiment_result["results"], out / "hits_distribution.png", plt)

    logger.info("Report complete: %s", out)
    return out


def _slim_for_json(result: dict) -> dict:
    """Remove large arrays before serialisation."""
    slim = {k: v for k, v in result.items() if k != "results"}
    slim["results"] = []
    for entry in result.get("results", []):
        e = {k: v for k, v in entry.items()
             if k not in ("equity_curve", "raw_results")}
        # hits_distribution: convert int keys to str for JSON
        if "hits_distribution" in e:
            e["hits_distribution"] = {str(k): v for k, v in e["hits_distribution"].items()}
        slim["results"].append(e)
    return slim


def _build_markdown(result: dict) -> str:
    lines = [
        "# Lotofácil Lab — Relatório de Ablação",
        "",
        f"**Data:** {result.get('started_at', '?')}  ",
        f"**Concursos de teste:** {result.get('n_test', '?')}  ",
        f"**Total de sorteios usados:** {result.get('n_draws_total', '?')}  ",
        f"**Custo por jogo:** R${COST_PER_GAME:.2f}",
        "",
        "## Comparação ROI",
        "",
        "| Config | Acertos médios | ROI % | Sharpe | MaxDD (R$) | p-value vs random |",
        "|--------|---------------|-------|--------|------------|-------------------|",
    ]

    for entry in result.get("results", []):
        if "error" in entry:
            lines.append(f"| {entry['name']} | ERRO | — | — | — | — |")
            continue
        lines.append(
            f"| {entry.get('name', '?')} "
            f"| {entry.get('mean_hits', 0):.4f} "
            f"| {entry.get('roi_pct', 0):.2f}% "
            f"| {entry.get('sharpe', 0):.4f} "
            f"| {entry.get('max_drawdown', 0):.2f} "
            f"| {entry.get('p_value_vs_random', 1):.4f} |"
        )

    # Find best neural model
    neural_entries = [e for e in result.get("results", [])
                      if e.get("name", "").startswith("neural_") and "error" not in e]
    random_entry = next((e for e in result.get("results", []) if e.get("name") == "random"), None)

    lines += ["", "## Interpretação"]

    if neural_entries and random_entry:
        best = neural_entries[0]  # already sorted by mean_hits
        diff = best.get("mean_hits", 0) - random_entry.get("mean_hits", 0)
        p = best.get("p_value_vs_random", 1.0)
        if p < 0.05:
            lines.append(
                f"O melhor modelo (`{best['name']}`) supera o baseline aleatório em "
                f"**{diff:.4f} acertos médios** (p={p:.4f} < 0.05) — ganho estatisticamente significativo."
            )
        else:
            lines.append(
                f"O melhor modelo (`{best['name']}`) apresenta p={p:.4f} ≥ 0.05 — ganho "
                "dentro da margem de ruído, não estatisticamente significativo."
            )

        # Climate/lunar check
        has_clima = any("clima" in e.get("name", "") and "error" not in e for e in neural_entries)
        has_lua = any("lua" in e.get("name", "") and "error" not in e for e in neural_entries)
        base_only = next((e for e in neural_entries if e.get("name") == "neural_base+temp+priors"), None)

        if has_clima and base_only:
            clima_entry = next((e for e in neural_entries if "clima" in e.get("name", "")), None)
            if clima_entry:
                delta = clima_entry.get("mean_hits", 0) - base_only.get("mean_hits", 0)
                verdict = "agrega valor" if delta > 0.02 else "dentro do ruído"
                lines.append(f"\n**Clima:** delta_hits={delta:.4f} — {verdict}.")

        if has_lua and base_only:
            lua_entry = next((e for e in neural_entries if "lua" in e.get("name", "") and "clima" not in e.get("name", "")), None)
            if lua_entry:
                delta = lua_entry.get("mean_hits", 0) - base_only.get("mean_hits", 0)
                verdict = "agrega valor" if delta > 0.02 else "dentro do ruído"
                lines.append(f"\n**Lua:** delta_hits={delta:.4f} — {verdict}.")

    lines += [
        "",
        "## Recomendação",
        "",
        "Use a config com melhor ROI ajustado por risco (Sharpe) e p-value < 0.05.",
        "Features sem ganho estatístico devem ser desativadas para reduzir overfitting.",
        "",
        "_Relatório gerado automaticamente pelo lotofacil_lab._",
    ]
    return "\n".join(lines)


def _plot_equity_curves(results: List[dict], path: Path, plt) -> None:
    try:
        fig, ax = plt.subplots(figsize=(12, 6))
        for entry in results:
            curve = entry.get("equity_curve", [])
            if not curve:
                continue
            ax.plot(curve, label=entry.get("name", "?"), alpha=0.8)
        ax.axhline(0, color="black", linestyle="--", linewidth=0.8)
        ax.set_xlabel("Concurso de teste")
        ax.set_ylabel("Equity acumulada (R$)")
        ax.set_title("Curvas de Equity — Ablação")
        ax.legend(fontsize=8, loc="lower left")
        plt.tight_layout()
        plt.savefig(path, dpi=120)
        plt.close(fig)
        logger.info("Written: %s", path)
    except Exception as exc:
        logger.warning("Could not generate equity curve plot: %s", exc)


def _plot_hits_distribution(results: List[dict], path: Path, plt) -> None:
    try:
        entries = [e for e in results if e.get("hits_distribution")]
        if not entries:
            return

        n_configs = len(entries)
        fig, axes = plt.subplots(1, n_configs, figsize=(4 * n_configs, 5), sharey=False)
        if n_configs == 1:
            axes = [axes]

        for ax, entry in zip(axes, entries):
            dist = entry.get("hits_distribution", {})
            keys = sorted(int(k) for k in dist)
            vals = [dist.get(k, 0) for k in keys]
            ax.bar(keys, vals, color="steelblue", alpha=0.8)
            ax.set_title(entry.get("name", "?"), fontsize=8)
            ax.set_xlabel("Acertos")
            ax.set_ylabel("Concursos")

        plt.suptitle("Distribuição de Acertos por Config")
        plt.tight_layout()
        plt.savefig(path, dpi=120)
        plt.close(fig)
        logger.info("Written: %s", path)
    except Exception as exc:
        logger.warning("Could not generate hits distribution plot: %s", exc)
