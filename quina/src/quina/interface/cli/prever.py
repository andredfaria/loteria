"""prever command — predict next Quina draw using trained ensemble model."""
from __future__ import annotations


import typer
from rich.console import Console
from rich.table import Table

from quina.infra.config import NUMEROS_POR_SORTEIO, TOTAL_NUMEROS
from quina.servicos.listar_modelos_treinados import listar_modelos_treinados
from quina.servicos.gerar_predicao import gerar_predicao

app = typer.Typer(help="Predizer o próximo sorteio da Quina.")
console = Console()


@app.command()
def prever() -> None:
    """Gera predição para o próximo concurso usando o ensemble treinado."""
    modelos = listar_modelos_treinados()
    if modelos.total == 0:
        console.print("[red]Nenhum modelo treinado. Execute: quina modelo treinar --ml[/red]")
        raise typer.Exit(1)

    console.print("[cyan]Gerando predição com ensemble treinado...[/cyan]")
    try:
        resultado = gerar_predicao()
    except Exception as exc:
        console.print(f"[red]Erro ao gerar predição: {exc}[/red]")
        raise typer.Exit(1) from exc

    prob_real_pct = NUMEROS_POR_SORTEIO / TOTAL_NUMEROS * 100

    table = Table(title=f"Predição para o Concurso {resultado.concurso_alvo}")
    table.add_column("Dezenas")
    table.add_column("Score de Confiança (0-100)")
    table.add_column("Probabilidade Real")
    table.add_row(
        " - ".join(f"{d:02d}" for d in resultado.dezenas),
        f"{resultado.confianca_media * 100:.2f}",
        f"{prob_real_pct:.2f}%",
    )
    console.print(table)
    console.print(
        f"[dim]Score de confiança é um ranking do modelo, não uma probabilidade "
        f"estatística. A chance real de qualquer dezena sair é sempre "
        f"{prob_real_pct:.2f}%.[/dim]"
    )

    console.print(f"[dim]Scores individuais (ranking do modelo, não probabilidade):[/dim]")
    for n, p in zip(resultado.dezenas, resultado.probabilidades):
        console.print(f"  {n:02d}: {p:.4f}")