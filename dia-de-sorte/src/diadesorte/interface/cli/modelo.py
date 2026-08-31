from __future__ import annotations

import logging
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore", category=UserWarning, module="sklearn")

_SRC = Path(__file__).resolve().parent.parent.parent.parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import typer
from rich.console import Console
from rich.table import Table

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")

import numpy as np

from diadesorte.infra.config import DADOS_DIR, MODELOS_DIR, NUMEROS_POR_SORTEIO, TOTAL_NUMEROS
from diadesorte.infra.dados.leitor import load_draws
from diadesorte.infra.modelos.ensemble import EnsemblePredictor
from diadesorte.infra.geracao.optimizers import gerar_jogo

app = typer.Typer(help="Modelo ML — treinar e prever.")
console = Console()


@app.command()
def treinar() -> None:
    """Treina o ensemble de modelos com todos os dados históricos."""
    draws = load_draws(DADOS_DIR)
    if len(draws) < 50:
        console.print("[red]ERRO: Menos de 50 sorteios disponíveis.[/red]")
        raise typer.Exit(1)

    console.print(f"[cyan]Carregados {len(draws)} sorteios[/cyan]")
    console.print("[cyan]Treinando EnsemblePredictor (Frequency + ML + Probabilistic)...[/cyan]")

    predictor = EnsemblePredictor()
    predictor.fit(draws)
    predictor.save()

    console.print(f"[green]Modelos salvos em: {MODELOS_DIR}[/green]")

    scores = predictor.score_dict()
    prob_real_pct = NUMEROS_POR_SORTEIO / TOTAL_NUMEROS * 100
    table = Table(title="Top 10 Números por Score do Modelo")
    table.add_column("Nº", style="cyan")
    table.add_column("Score (0-100)", style="green")
    table.add_column("Probabilidade Real", style="blue")
    table.add_column("Frequência Total", style="yellow")

    sorted_nums = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    freq_total = {n: 0 for n in range(1, TOTAL_NUMEROS + 1)}
    for d in draws:
        for n in d.dezenas:
            freq_total[n] += 1

    for num, score in sorted_nums[:10]:
        table.add_row(f"{num:02d}", f"{score*100:.2f}", f"{prob_real_pct:.2f}%", f"{freq_total[num]}x")

    console.print(table)
    console.print(
        f"[dim]Score é um ranking do modelo, não probabilidade. A chance real "
        f"de qualquer número sair é sempre {prob_real_pct:.2f}%.[/dim]"
    )


@app.command()
def prever() -> None:
    """Gera um jogo para o próximo concurso usando o modelo treinado."""
    draws = load_draws(DADOS_DIR)
    if len(draws) < 50:
        console.print("[red]ERRO: Menos de 50 sorteios disponíveis.[/red]")
        raise typer.Exit(1)

    ultimo = draws[-1]
    console.print(f"[cyan]Último sorteio: Concurso {ultimo.concurso} ({ultimo.data})[/cyan]")
    console.print(f"  Números: {' '.join(f'{n:02d}' for n in ultimo.dezenas)}")
    console.print(f"  Mês: {ultimo.mes_sorte}")
    console.print()

    predictor = EnsemblePredictor()
    predictor.load()
    if not predictor._fitted:
        console.print("[yellow]Modelo não encontrado. Treinando agora...[/yellow]")
        predictor.fit(draws)
        predictor.save()

    console.print("[cyan]Otimizando jogo via Simulated Annealing...[/cyan]")
    jogo = gerar_jogo(predictor, draws, ultimo_sorteio=ultimo.dezenas)

    console.print()

    titulo = f"JOGO SUGERIDO — Concurso {ultimo.concurso + 1}"
    console.print("=" * 62, style="bold")
    console.print(
        f"  {titulo}  [aderência aos critérios: {jogo['score']:.1f}/100]",
        style="bold",
        markup=False,
    )
    console.print("=" * 62, style="bold")

    nums_str = "  ".join(f"{n:02d}" for n in jogo["numeros"])
    console.print(f"\n  [bold cyan]Números:[/bold cyan]     {nums_str}")
    console.print(f"  [bold cyan]Mês da Sorte:[/bold cyan] {jogo['mes_sorte']}")

    mj = jogo["metricas_jogo"]
    console.print(
        f"\n  Composição: {mj['pares']} par(es) / {mj['impares']} ímpar(es)"
        f"  |  {mj['baixos']} baixo(s) / {mj['altos']} alto(s)"
        f"  |  Soma: {mj['soma']}"
    )

    console.print("\n  [bold]Filtros Atendidos:[/bold]")
    filtros_nome = {
        "pares": "Paridade (2-5 pares)",
        "baixos": "Faixa (2-5 baixos)",
        "soma": "Soma (80-150)",
        "consecutivos": "Consecutivos (≥1 par)",
        "repeticoes": "Repetições (≤3 do anterior)",
    }
    for key, nome in filtros_nome.items():
        status = "✓" if jogo["filtros"].get(key) else "✗"
        cor = "green" if jogo["filtros"].get(key) else "red"
        console.print(f"    [{cor}]{status}[/{cor}] {nome}")

    prob_real_pct = NUMEROS_POR_SORTEIO / TOTAL_NUMEROS * 100
    console.print("\n  [bold]Score de cada número (0-100):[/bold]")
    console.print(
        f"  [dim](score é ranking do modelo, não probabilidade; a chance real "
        f"de qualquer número sair é sempre {prob_real_pct:.2f}%)[/dim]"
    )
    for n in jogo["numeros"]:
        score = jogo["scores"].get(n, 0)
        razao = jogo["razoes"].get(n, "")
        console.print(f"    {n:02d} → {score:.2f}  ({razao})")

    console.print()
    console.print(
        "[dim]NOTA: Este jogo é uma sugestão estatística baseada em análise histórica.\n"
        "      Não há garantia de acertos. Cada sorteio é independente.[/dim]"
    )
    console.print()


@app.command()
def probas() -> None:
    """Mostra o score de ranking do modelo para cada número (não é probabilidade)."""
    draws = load_draws(DADOS_DIR)
    if len(draws) < 50:
        console.print("[red]ERRO: Menos de 50 sorteios disponíveis.[/red]")
        raise typer.Exit(1)

    predictor = EnsemblePredictor()
    predictor.load()
    if not predictor._fitted:
        console.print("[yellow]Modelo não encontrado. Treinando agora...[/yellow]")
        predictor.fit(draws)
        predictor.save()

    scores = predictor.score_dict()
    prob_real_pct = NUMEROS_POR_SORTEIO / TOTAL_NUMEROS * 100
    freq_total = {n: 0 for n in range(1, TOTAL_NUMEROS + 1)}
    for d in draws:
        for n in d.dezenas:
            freq_total[n] += 1

    table = Table(title="Score por Número (não é probabilidade)")
    table.add_column("Nº", style="cyan")
    table.add_column("Score (0-100)", style="green")
    table.add_column("Probabilidade Real", style="blue")
    table.add_column("Freq. Total", style="yellow")
    table.add_column("Atraso", style="magenta")

    from diadesorte.infra.atributos.base import atraso
    at = atraso(draws, len(draws), max_atraso=50)

    sorted_nums = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    for num, score in sorted_nums:
        table.add_row(
            f"{num:02d}", f"{score*100:.2f}", f"{prob_real_pct:.2f}%",
            f"{freq_total[num]}x", f"{at[num]} concursos",
        )

    console.print(table)
    console.print(
        f"[dim]Score é um ranking do modelo, não probabilidade. A chance real "
        f"de qualquer número sair é sempre {prob_real_pct:.2f}%.[/dim]"
    )


@app.command()
def backtest() -> None:
    """Avalia o modelo em concursos passados (walk-forward)."""
    draws = load_draws(DADOS_DIR)
    if len(draws) < 100:
        console.print("[red]ERRO: Menos de 100 sorteios.[/red]")
        raise typer.Exit(1)

    n_testes = min(50, len(draws) // 3)
    step = max(1, (len(draws) - n_testes) // n_testes)

    hits_ml = []

    console.print(f"[cyan]Backtest walk-forward com até 20 testes...[/cyan]")

    with console.status("[cyan]Executando backtest (pode levar alguns minutos)...[/cyan]"):
        for i in range(len(draws) - n_testes, len(draws) - 1, step):
            if len(hits_ml) >= 20:
                break
            train = draws[:i]
            test = draws[i]

            pred = EnsemblePredictor()
            pred.fit(train)
            p = pred.score()
            top7 = sorted(np.argsort(p)[::-1][:7])
            top7 = [int(x + 1) for x in top7]
            hits_ml.append(len(set(top7) & set(test.dezenas)))

    hits_ml = np.array(hits_ml)

    console.print()
    table = Table(title=f"Backtest ML Ensemble ({len(hits_ml)} testes)")
    table.add_column("Métrica", style="cyan")
    table.add_column("ML Ensemble", style="green")
    table.add_column("Aleatório (esperado)", style="dim")

    aleatorio = 7 * 7 / 31

    table.add_row("Média de acertos", f"{hits_ml.mean():.3f}", f"{aleatorio:.3f}")
    table.add_row("≥ 4 acertos", f"{(hits_ml >= 4).sum()} ({(hits_ml >= 4).mean()*100:.0f}%)", "-")
    table.add_row("≥ 5 acertos", f"{(hits_ml >= 5).sum()} ({(hits_ml >= 5).mean()*100:.0f}%)", "-")
    console.print(table)

    console.print("\n[dim]NOTA: Em loterias, nenhum modelo supera significativamente o aleatório.\n"
                  "O valor está em estruturar o jogo com critérios estatísticos.\n"
                  "Cada sorteio é um evento independente.[/dim]")
    console.print()
