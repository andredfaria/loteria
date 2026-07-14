"""modelo subcommands — backtest de estratégias e leaderboard."""
from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from quina.infra.dados.banco import DatabaseManager
from quina.infra.dados.leitor import load_draws
from quina.servicos.backtest import ESTRATEGIAS_DISPONIVEIS, rodar_backtest
from quina.servicos.treinar_modelos import treinar_modelos as servico_treinar_ml

app = typer.Typer(help="Backtest de estratégias e leaderboard.")
console = Console()


@app.command()
def treinar(
    estrategia: str = typer.Option("filtros", "--estrategia", help=f"Uma de: {', '.join(ESTRATEGIAS_DISPONIVEIS)}"),
    janela: int = typer.Option(300, "--janela", help="Quantidade de concursos recentes usados no backtest"),
    ml: bool = typer.Option(False, "--ml", help="Treinar também modelos ML (RF+XGB+LGBM ensemble)"),
) -> None:
    """Roda backtest walk-forward da estratégia e salva no leaderboard."""
    db = DatabaseManager()
    if db.count_concursos() < 2:
        console.print("[red]Dados insuficientes. Execute: quina dados atualizar[/red]")
        raise typer.Exit(1)

    console.print(f"[cyan]Rodando backtest: estratégia={estrategia}, janela={janela}...[/cyan]")
    try:
        metricas = rodar_backtest(estrategia=estrategia, janela=janela, db=db)
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc
    db.salvar_backtest(estrategia, metricas["janela"], metricas)

    table = Table(title=f"Backtest — {estrategia}")
    table.add_column("Faixa")
    table.add_column("Taxa estratégia")
    table.add_column("Taxa baseline (aleatório)")
    for faixa in ["2", "3", "4", "5"]:
        table.add_row(
            faixa,
            f"{metricas['taxa_estrategia'][faixa]:.4f}",
            f"{metricas['taxa_baseline'][faixa]:.4f}",
        )
    console.print(table)
    console.print(f"[dim]{metricas['total_rodadas']} rodadas em {metricas['tempo_execucao_segundos']}s[/dim]")

    if ml:
        console.print("[cyan]Treinando modelos ML (RF+XGB+LGBM ensemble)...[/cyan]")
        from quina.infra.config import DADOS_DIR, MODELOS_DIR
        resultado = servico_treinar_ml(incluir_ml=True)
        console.print(f"[green]Modelos treinados: {', '.join(resultado.modelos_treinados)}[/green]")
        console.print(f"[dim]{resultado.total_concursos} concursos usados[/dim]")


@app.command()
def leaderboard(limite: int = typer.Option(20, "--limite")) -> None:
    """Lista os últimos backtests salvos."""
    db = DatabaseManager()
    registros = db.listar_backtests(limite=limite)
    if not registros:
        console.print("[yellow]Nenhum backtest encontrado. Execute: quina modelo treinar[/yellow]")
        raise typer.Exit(0)

    table = Table(title="Leaderboard de estratégias")
    table.add_column("ID")
    table.add_column("Estratégia")
    table.add_column("Janela")
    table.add_column("Taxa 5 acertos")
    table.add_column("Criado em")
    for r in registros:
        table.add_row(
            str(r["id"]), r["estrategia"], str(r["janela"]),
            f"{r['metricas']['taxa_estrategia']['5']:.4f}", r["criado_em"],
        )
    console.print(table)
