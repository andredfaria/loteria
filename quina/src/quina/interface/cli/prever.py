"""prever command — predict next Quina draw using trained ensemble model."""
from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from quina.infra.config import MODELOS_DIR
from quina.infra.dados.banco import DatabaseManager
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

    table = Table(title=f"Predição para o Concurso {resultado.concurso_alvo}")
    table.add_column("Dezenas")
    table.add_column("Confiança")
    table.add_row(
        " - ".join(f"{d:02d}" for d in resultado.dezenas),
        f"{resultado.confianca_media:.2%}",
    )
    console.print(table)

    console.print(f"[dim]Probabilidades individuais: ")
    for n, p in zip(resultado.dezenas, resultado.probabilidades):
        console.print(f"  {n:02d}: {p:.4f}")