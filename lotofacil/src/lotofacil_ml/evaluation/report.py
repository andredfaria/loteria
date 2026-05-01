"""Terminal and file report generation using Rich."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from lotofacil_ml.config import HIT_THRESHOLDS
from lotofacil_ml.evaluation.metrics import LotofacilMetrics

logger = logging.getLogger(__name__)
console = Console()


class ReportGenerator:

    def __init__(self, metrics: Optional[LotofacilMetrics] = None):
        self.metrics = metrics or LotofacilMetrics()

    def generate_terminal_report(self, results: List[dict]) -> None:
        """Print a rich-formatted report to the terminal."""
        if not results:
            console.print("[red]No results to report.[/red]")
            return

        dist = self.metrics.distribution_of_hits(results)
        mean_acc = self.metrics.mean_accuracy(results)
        rp = self.metrics.recall_precision(results)
        baseline = self.metrics.vs_random_baseline(results)

        console.print()
        console.print(Panel(
            f"[bold cyan]Lotofácil ML — Backtest Report[/bold cyan]\n"
            f"Concursos avaliados: [yellow]{len(results)}[/yellow]  "
            f"| Gerado em: [dim]{datetime.now():%d/%m/%Y %H:%M}[/dim]",
            box=box.DOUBLE_EDGE,
        ))

        # Hit distribution table
        table = Table(title="Distribuição de Acertos", box=box.SIMPLE_HEAVY)
        table.add_column("Acertos", style="cyan", justify="center")
        table.add_column("Jogos", style="white", justify="center")
        table.add_column("% do Total", style="green", justify="center")
        total = len(results)
        for threshold in HIT_THRESHOLDS:
            count = dist[threshold]
            pct = count / total * 100 if total else 0
            table.add_row(str(threshold), str(count), f"{pct:.1f}%")
        console.print(table)

        # Summary metrics
        summary = Table(title="Métricas Gerais", box=box.SIMPLE_HEAVY)
        summary.add_column("Métrica", style="cyan")
        summary.add_column("Valor", style="white", justify="right")
        summary.add_row("Média de acertos", f"{mean_acc:.2f}")
        summary.add_row("Precisão", f"{rp['precision']:.3f}")
        summary.add_row("Recall", f"{rp['recall']:.3f}")
        summary.add_row("Baseline aleatório (média)", f"{baseline['random_mean']:.2f}")
        summary.add_row("Melhoria vs baseline", f"{baseline['improvement_pct']:+.2f}%")
        summary.add_row("p-value (vs random)", f"{baseline['p_value']:.4f}")
        console.print(summary)

        if baseline["improvement_pct"] > 0:
            console.print(f"[green]O modelo supera o baseline em {baseline['improvement_pct']:.2f}%[/green]")
        else:
            console.print(f"[red]O modelo não supera o baseline aleatório[/red]")
        console.print()

    def export_txt_report(self, results: List[dict], path: Path) -> None:
        """Write a plain-text report to disk."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        dist = self.metrics.distribution_of_hits(results)
        mean_acc = self.metrics.mean_accuracy(results)
        rp = self.metrics.recall_precision(results)
        baseline = self.metrics.vs_random_baseline(results)

        lines = [
            "=" * 60,
            "  LOTOFÁCIL ML — BACKTEST REPORT",
            f"  Gerado em: {datetime.now():%d/%m/%Y %H:%M:%S}",
            "=" * 60,
            "",
            f"Concursos avaliados: {len(results)}",
            "",
            "DISTRIBUIÇÃO DE ACERTOS",
            "-" * 30,
        ]
        total = len(results)
        for t in HIT_THRESHOLDS:
            count = dist[t]
            pct = count / total * 100 if total else 0
            lines.append(f"  {t} acertos: {count:4d}  ({pct:.1f}%)")
        lines += [
            "",
            "MÉTRICAS GERAIS",
            "-" * 30,
            f"  Média de acertos:         {mean_acc:.2f}",
            f"  Precisão:                 {rp['precision']:.3f}",
            f"  Recall:                   {rp['recall']:.3f}",
            f"  Baseline aleatório:       {baseline['random_mean']:.2f}",
            f"  Melhoria vs baseline:     {baseline['improvement_pct']:+.2f}%",
            f"  p-value (vs random):      {baseline['p_value']:.4f}",
            "",
            "=" * 60,
        ]
        path.write_text("\n".join(lines), encoding="utf-8")
        logger.info("Report exported to %s", path)
