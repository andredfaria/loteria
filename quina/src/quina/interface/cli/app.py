"""Unified CLI entry point for the Quina Prediction System."""
from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent.parent.parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import typer
from rich.console import Console

from quina.interface.cli.dados import app as dados_app
from quina.interface.cli.jogos import app as jogos_app
from quina.interface.cli.modelo import app as modelo_app
from quina.interface.cli.portfolio import app as portfolio_app

app = typer.Typer(
    name="quina",
    help="Sistema de previsão Quina — dados, modelos, portfólio e experimentos.",
    add_completion=False,
)
console = Console()

app.add_typer(dados_app, name="dados")
app.add_typer(modelo_app, name="modelo")
app.add_typer(jogos_app, name="jogos")
app.add_typer(portfolio_app, name="portfolio")


if __name__ == "__main__":
    app()
