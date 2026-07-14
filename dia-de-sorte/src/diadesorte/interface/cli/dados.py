from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from diadesorte.infra.dados.api_caixa import DiadesorteFetcher
from diadesorte.infra.dados.banco import DatabaseManager

app = typer.Typer(help="Gerenciamento de dados — coleta e status.")
console = Console()


@app.command()
def atualizar() -> None:
    """Sincroniza concursos novos da API da Caixa com o banco local."""
    fetcher = DiadesorteFetcher()
    console.print("[cyan]Verificando concursos novos na API...[/cyan]")
    novos = fetcher.sync_new_draws()
    if novos:
        console.print(f"[green]OK {novos} concurso(s) sincronizado(s)[/green]")
    else:
        console.print("[dim]Dados: já atualizados[/dim]")


@app.command()
def status() -> None:
    """Mostra total de concursos e o último concurso sincronizado."""
    db = DatabaseManager()
    total = db.count_concursos()
    if total == 0:
        console.print("[yellow]Nenhum concurso encontrado no banco.[/yellow]")
        console.print("Execute: [cyan]diadesorte dados atualizar[/cyan]")
        raise typer.Exit(0)

    latest = db.get_latest_concurso()
    table = Table(show_header=False, box=None)
    table.add_row("Total de concursos:", str(total))
    table.add_row("Último concurso:", str(latest["concurso"]))
    table.add_row("Data:", latest["data"])
    table.add_row("Dezenas:", "  ".join(f"{n:02d}" for n in latest["dezenas"]))
    table.add_row("Mês da Sorte:", latest["mes_sorte"])
    console.print(table)
