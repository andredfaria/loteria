"""portfolio subcommand — geração de portfólio de jogos por orçamento."""
from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from quina.infra.dados.banco import DatabaseManager
from quina.servicos.portfolio import PERFIS_TAMANHOS, gerar_portfolio

app = typer.Typer(help="Geração de portfólio de jogos por orçamento.")
console = Console()


@app.callback()
def _callback() -> None:
    """Geração de portfólio de jogos por orçamento."""


@app.command()
def gerar(
    orcamento: float = typer.Option(..., "--orcamento"),
    perfil: str = typer.Option("equilibrado", "--perfil", help=f"Um de: {', '.join(PERFIS_TAMANHOS)}"),
) -> None:
    """Gera um portfólio de jogos que respeita o orçamento informado."""
    db = DatabaseManager()
    draws = db.get_all_concursos()
    if len(draws) < 2:
        console.print("[red]Dados insuficientes. Execute: quina dados atualizar[/red]")
        raise typer.Exit(1)

    try:
        resultado = gerar_portfolio(orcamento=orcamento, perfil=perfil, draws=draws)
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc

    table = Table(title=f"Portfólio — {perfil}")
    table.add_column("Dezenas")
    table.add_column("Tamanho")
    table.add_column("Custo")
    for jogo in resultado["jogos"]:
        table.add_row(
            "  ".join(f"{d:02d}" for d in jogo["dezenas"]),
            str(jogo["tamanho_aposta"]),
            f"R$ {jogo['custo']:.2f}",
        )
    console.print(table)
    console.print(
        f"[dim]Custo total: R$ {resultado['custo_total']:.2f} — "
        f"sobra: R$ {resultado['orcamento_sobra']:.2f}[/dim]"
    )
