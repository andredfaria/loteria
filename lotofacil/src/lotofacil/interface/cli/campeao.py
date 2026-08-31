"""campeao subcommand — champion game combining all strategies via cross-referencing."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    # Só para tipagem: em runtime o import fica dentro do comando, para não
    # puxar o serviço (e TensorFlow junto) no --help. Sem esta linha a
    # anotação de _exibir_campeao referencia um nome inexistente no módulo.
    from lotofacil.servicos.gerar_campeao import ResultadoCampeao

_SRC = Path(__file__).resolve().parent.parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import typer
from rich.console import Console
from rich.panel import Panel
from rich import box

app = typer.Typer(help="Campeão — combina todas as estratégias, cruza consenso e retorna o top-3.")
console = Console()


@app.command()
def gerar(
    concurso: Optional[int] = typer.Option(None, "--concurso", "-c", help="Concurso alvo (padrão: próximo após o último)"),
) -> None:
    """Gera o campeão (top-3) para o concurso alvo cruzando todas as estratégias."""
    from lotofacil.infra.dados.leitor import load_draws
    from lotofacil.infra.config import DADOS_DIR
    from lotofacil.servicos.gerar_campeao import gerar_campeao

    draws = load_draws(DADOS_DIR)
    if not draws:
        console.print("[red]Sem dados. Execute: lotofacil dados atualizar[/red]")
        raise typer.Exit(1)

    if concurso is None:
        concurso = draws[-1].concurso + 1

    try:
        resultado = gerar_campeao(concurso)
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1)

    _exibir_campeao(console, resultado, draws[-1].concurso)


def _exibir_campeao(console: Console, r: ResultadoCampeao, ultimo_local: int) -> None:
    console.print(f"\n{'═'*60}")
    console.print(f"  [bold cyan]🏆 CAMPEÃO LOTOFÁCIL — Concurso {r.concurso_alvo}[/bold cyan]")
    console.print(f"  {r.total_candidatos} candidatos gerados · {len(r.estrategias_ativas)} estratégias ativas")
    console.print(f"  Último concurso usado: {r.ultimo_concurso}")
    console.print(f"{'═'*60}")

    for jogo in r.top_3:
        dezenas = "  ".join(f"{n:02d}" for n in jogo["dezenas"])
        probas = [(n, r.probabilidades[n - 1] * 100) for n in jogo["dezenas"]]
        probas_linha = "  ".join(f"[green]{n:02d}[/green]:{p:.2f}%" for n, p in probas)
        console.print(Panel(
            f"[bold yellow]Jogo {jogo['posicao']}[/bold yellow]  {dezenas}\n\n"
            f"Probabilidade por número:\n{probas_linha}\n\n"
            f"Combined: [green]{jogo['combined_score']:.4f}[/green]  "
            f"Proba: {jogo['proba_score']:.4f}  "
            f"Filtros: {jogo['filter_score']:.4f}  "
            f"Consenso: {jogo['consensus_score']:.4f}  "
            f"Qualidade: [cyan]{jogo['qualidade']}/7[/cyan]\n"
            f"Soma {jogo['filtros']['soma']} · {jogo['filtros']['pares']} · "
            f"{jogo['filtros']['repetidos']} repetidos do último · "
            f"{jogo['filtros']['moldura']} moldura · "
            f"{jogo['filtros']['primos']} primos · "
            f"{jogo['filtros']['fibonacci']} fib · "
            f"{jogo['filtros']['consecutivos']} consecutivos",
            box=box.ROUNDED,
        ))

    console.print(f"\n  Estratégias ativas: [cyan]{', '.join(r.estrategias_ativas)}[/cyan]")
    console.print(f"  💾 Salvo em saida/jogos/campeao_{r.concurso_alvo}.json")
    console.print(f"{'═'*60}\n")
