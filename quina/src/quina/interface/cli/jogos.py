"""jogos subcommands — geração de jogos e fechamento."""
from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from quina.dominio.regras import custo_aposta
from quina.infra.dados.banco import DatabaseManager
from quina.servicos import fechamento as fechamento_servico
from quina.servicos.estrategias import scoring
from quina.servicos.estrategias.frequencia_atraso import gerar_candidato_frequencia_atraso

app = typer.Typer(help="Geração de jogos: filtros/frequência+atraso e fechamento.")
console = Console()


@app.command()
def gerar(
    estrategia: str = typer.Option("filtros", "--estrategia"),
    tamanho: int = typer.Option(5, "--tamanho", help="Tamanho da aposta (5-15)"),
    n: int = typer.Option(5, "--n", help="Quantidade de jogos a gerar"),
    concurso_alvo: int = typer.Option(None, "--concurso-alvo", help="Concurso a validar depois (opcional)"),
) -> None:
    """Gera N jogos com a estratégia escolhida e persiste no banco."""
    db = DatabaseManager()
    draws = db.get_all_concursos()
    if len(draws) < 2:
        console.print("[red]Dados insuficientes. Execute: quina dados atualizar[/red]")
        raise typer.Exit(1)

    if estrategia == "filtros":
        candidatos = scoring.gerar_candidatos(quantidade=max(200, n * 20), tamanho_aposta=tamanho, draws=draws)
        selecionados = scoring.top_k(candidatos, n)
    elif estrategia == "frequencia_atraso":
        selecionados = [gerar_candidato_frequencia_atraso(draws, tamanho) for _ in range(n)]
    else:
        console.print(f"[red]Estratégia desconhecida: {estrategia}[/red]")
        raise typer.Exit(1)

    custo_unitario = custo_aposta(tamanho)
    table = Table(title=f"Jogos gerados — {estrategia}")
    table.add_column("Dezenas")
    table.add_column("Score")
    for jogo in selecionados:
        db.salvar_jogo_gerado(
            estrategia=estrategia, tamanho_aposta=tamanho, dezenas=jogo["dezenas"],
            score=jogo.get("score"), custo=custo_unitario, concurso_alvo_validacao=concurso_alvo,
        )
        table.add_row("  ".join(f"{d:02d}" for d in jogo["dezenas"]), f"{jogo.get('score', 0):.3f}")
    console.print(table)
    console.print(f"[dim]Custo total: R$ {custo_unitario * n:.2f}[/dim]")


@app.command()
def fechamento(
    dezenas: str = typer.Option(..., "--dezenas", help="Pool de dezenas separadas por vírgula, ex: 1,5,12,20,33,47"),
    garantia: str = typer.Option(..., "--garantia", help="k,faixa — ex: 4,4 garante quadra se 4 do pool saírem"),
) -> None:
    """Gera cobertura de fechamento (greedy) para o pool e garantia informados."""
    pool = [int(d.strip()) for d in dezenas.split(",")]
    k_str, faixa_str = garantia.split(",")
    resultado = fechamento_servico.gerar_fechamento(pool, (int(k_str), int(faixa_str)))

    table = Table(title="Fechamento")
    table.add_column("Jogo")
    for jogo in resultado["jogos"]:
        table.add_row("  ".join(f"{d:02d}" for d in jogo))
    console.print(table)
    console.print(f"[dim]{resultado['quantidade']} jogos — custo total R$ {resultado['custo_total']:.2f}[/dim]")
