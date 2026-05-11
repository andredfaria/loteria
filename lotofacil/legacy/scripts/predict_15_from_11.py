#!/usr/bin/env python
"""Generate 15 numbers using 11-number neural model + 15-number statistical filters.

Strategy:
1. Load historical draws
2. Use neural model (trained for 11 numbers) to get probabilities
3. Use Simulated Annealing with 15-number filters to select optimal 15 numbers
4. Display statistics
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import numpy as np
from rich.console import Console
from rich.table import Table

from data.loader import load_draws
from strategies.eleven_numbers.approaches.neural import NeuralApproach
from strategies.quinze_numbers.post_processor import sa_with_restarts, filter_score as filter_score_15
from core.lottery import estatisticas_dezenas

console = Console()


def main():
    console.print("[bold]═══════════════════════════════════════════════════════[/bold]")
    console.print("[bold]  15 Números — Baseado no Modelo Neural de 11[/bold]")
    console.print("[bold]═══════════════════════════════════════════════════════[/bold]\n")

    # 1. Load draws
    console.print("[bold]1. Carregando dados...[/bold]")
    draws = load_draws(source="db")
    console.print(f"   Sorteios carregados: {len(draws)}")
    console.print(f"   Último: Concurso {draws[-1].concurso} ({draws[-1].data})")

    # 2. Load trained neural model (11-number)
    console.print("\n[bold]2. Carregando modelo neural (11 números)...[/bold]")
    neural = NeuralApproach()
    try:
        neural.load()
        console.print("   Modelo carregado com sucesso!")
    except Exception:
        console.print("[yellow]   Modelo não encontrado. Treinando...[/yellow]")
        neural.fit(draws)
        neural.save()
        console.print("   Treino completo!")

    # 3. Get probabilities from 11-number model
    console.print("\n[bold]3. Obtendo probabilidades do modelo neural...[/bold]")
    probas = neural.predict_proba(draws)

    # Show top 15 by raw neural probability
    top15_raw = sorted(np.argsort(probas)[::-1][:15] + 1)
    console.print(f"   Top 15 (raw): {top15_raw}")

    # 4. Optimize 15 numbers using Simulated Annealing with 15-number filters
    console.print("\n[bold]4. Otimizando 15 números com Simulated Annealing + filtros estatísticos...[/bold]")
    last_draw = draws[-1].dezenas
    optimized_15 = sa_with_restarts(
        probas,
        last_draw=last_draw,
        n_restarts=5,
        iterations_per_restart=8000,
    )

    # 5. Display results
    console.print(f"\n[bold green]Jogo Otimizado para Concurso {draws[-1].concurso + 1}:[/bold green]")
    nums_str = ", ".join(f"{n:02d}" for n in optimized_15)
    console.print(f"[bold green][{nums_str}][/bold green]\n")

    # 6. Statistics
    stats = estatisticas_dezenas(optimized_15)
    fscore = filter_score_15(set(optimized_15), last_draw)

    table = Table(title="Estatísticas do Jogo (15 números)")
    table.add_column("Métrica", style="cyan")
    table.add_column("Valor", style="green")
    table.add_column("Faixa Ideal", style="yellow")

    table.add_row("Soma", str(stats["soma"]), "171–220")
    table.add_row("Pares", str(stats["pares"]), "7–8")
    table.add_row("Ímpares", str(stats["impares"]), "7–8")
    table.add_row("Moldura", str(stats["moldura"]), "9–10")
    table.add_row("Primos", str(stats["primos"]), "4–7")
    table.add_row("Fibonacci", str(stats["fibonacci"]), "3–5")
    table.add_row("Consecutivos", str(stats["consecutivos"]), "≥2")
    table.add_row("Repetidos do anterior", str(stats.get("repetidos", len(set(optimized_15) & set(last_draw)))), "8–10")

    console.print(table)

    console.print(f"\n[bold]Filter Score:[/bold] {fscore:.2f}")

    # 7. Comparison
    console.print(f"\n[bold]Comparação com Top 15 Raw:[/bold]")
    raw_stats = estatisticas_dezenas(top15_raw)
    raw_fscore = filter_score_15(set(top15_raw), last_draw)

    table2 = Table()
    table2.add_column("Métrica", style="cyan")
    table2.add_column("Raw (Top 15)", style="blue")
    table2.add_column("Otimizado (SA)", style="green")

    table2.add_row("Soma", str(raw_stats["soma"]), str(stats["soma"]))
    table2.add_row("Pares", str(raw_stats["pares"]), str(stats["pares"]))
    table2.add_row("Moldura", str(raw_stats["moldura"]), str(stats["moldura"]))
    table2.add_row("Primos", str(raw_stats["primos"]), str(stats["primos"]))
    table2.add_row("Fibonacci", str(raw_stats["fibonacci"]), str(stats["fibonacci"]))
    table2.add_row("Filter Score", f"{raw_fscore:.2f}", f"{fscore:.2f}")

    console.print(table2)

    console.print(f"\n[dim]Baseado no modelo neural de 11 números + filtros estatísticos de 15 números[/dim]")


if __name__ == "__main__":
    main()
