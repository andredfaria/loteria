"""dados subcommands — data update and status."""
from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import typer
from rich.console import Console

app = typer.Typer(help="Gerenciamento de dados — coleta e status.")
console = Console()


@app.command()
def atualizar(
    all: bool = typer.Option(False, "--all", help="Carrega todos os draws dos arquivos locais"),
    latest: bool = typer.Option(False, "--latest", help="Busca apenas o sorteio mais recente da API"),
) -> None:
    """Sincroniza novos concursos da API para o banco de dados."""
    from lotofacil_ml.data.database import DatabaseManager
    from lotofacil_ml.data.fetcher import LotofacilFetcher

    db = DatabaseManager()
    fetcher = LotofacilFetcher(db)

    if all:
        console.print("[cyan]Carregando todos os dados locais...[/cyan]")
        draws = fetcher.fetch_all_results()
        console.print(f"[green]✓ {len(draws)} concursos importados[/green]")
    elif latest:
        console.print("[cyan]Buscando sorteio mais recente da API...[/cyan]")
        draw = fetcher.fetch_latest()
        if draw:
            console.print(f"[green]✓ Concurso {draw['concurso']} ({draw['data']})[/green]")
        else:
            console.print("[red]Não foi possível buscar o sorteio mais recente.[/red]")
            raise typer.Exit(1)
    else:
        console.print("[cyan]Sincronizando novos sorteios...[/cyan]")
        n = fetcher.sync_new_draws()
        console.print(f"[green]✓ {n} novos sorteios sincronizados[/green]")

    _atualizar_complementos(db, console)


def _atualizar_complementos(db, console) -> None:
    """Atualiza dados de clima e lua para os sorteios recentes faltantes."""
    _backfill_clima(console)
    _backfill_lua(db, console)


def _backfill_clima(console) -> None:
    try:
        from lotofacil_lab.coleta.backfill_clima_archive import backfill
    except ImportError:
        console.print("[yellow]⚠ Clima: módulo lotofacil_lab não disponível[/yellow]")
        return
    console.print("[cyan]Atualizando dados climáticos...[/cyan]")
    try:
        count = backfill(ultimos=100, force=False)
        if count:
            console.print(f"[green]✓ Clima: {count} concursos atualizados[/green]")
        else:
            console.print("[dim]Clima: já atualizado[/dim]")
    except Exception as exc:
        console.print(f"[yellow]⚠ Erro ao atualizar clima: {exc}[/yellow]")


def _backfill_lua(db, console) -> None:
    try:
        from lotofacil_lab.data.lunar_loader import compute_lunar_features, _parse_iso
    except ImportError:
        console.print("[yellow]⚠ Lua: módulo lotofacil_lab não disponível[/yellow]")
        return
    console.print("[cyan]Atualizando dados lunares...[/cyan]")
    draws = db.get_all_concursos()
    if not draws:
        return
    recent = draws[-100:]
    computed = 0
    for draw in recent:
        iso = _parse_iso(str(draw["data"]))
        if iso:
            compute_lunar_features(iso)
            computed += 1
    console.print(f"[green]✓ Lua: {computed} datas cacheadas[/green]")


@app.command()
def status() -> None:
    """Mostra o último concurso, total de draws e período coberto."""
    from lotofacil_ml.data.database import DatabaseManager

    db = DatabaseManager()
    count = db.count_concursos()
    latest = db.get_latest_concurso()

    console.print(f"[bold]Status do banco de dados[/bold]")
    console.print(f"Total de concursos: [cyan]{count}[/cyan]")
    if latest:
        console.print(f"Mais recente: Concurso [cyan]{latest['concurso']}[/cyan] ({latest['data']})")
    else:
        console.print("[yellow]Sem dados. Execute: lotofacil dados atualizar --all[/yellow]")
