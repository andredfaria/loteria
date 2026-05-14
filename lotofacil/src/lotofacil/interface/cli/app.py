"""Unified CLI entry point for Lotofácil Prediction System."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

_SRC = Path(__file__).resolve().parent.parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import json
import typer
from rich.console import Console
from rich.panel import Panel
from rich import box

app = typer.Typer(
    name="lotofacil",
    help="Sistema de previsão Lotofácil — dados, modelos, portfólio e experimentos.",
    add_completion=False,
)
console = Console()


@app.command()
def prever(
    abordagem: str = typer.Option(
        "todas", "--abordagem", "-a",
        help="Abordagem: statistical, ml, neural, todas",
    ),
    concurso: Optional[int] = typer.Option(None, "--concurso", "-c", help="Concurso alvo"),
) -> None:
    """Prediz 11 números para o próximo concurso."""
    from lotofacil.infra.config import DADOS_DIR, SAIDA_DIR
    from lotofacil.infra.dados.leitor import load_draws
    from lotofacil.infra.estrategias.onze_dezenas.predictor import ElevenNumbersStrategy

    draws = load_draws(DADOS_DIR)

    if not draws:
        console.print("[red]Sem dados. Execute: lotofacil dados atualizar[/red]")
        raise typer.Exit(1)

    console.print(f"  [dim]{len(draws)} concursos carregados[/dim]")

    approach_map = {"todas": "all", "estatistica": "statistical", "statistical": "statistical", "ml": "ml", "neural": "neural"}
    engine_approach = approach_map.get(abordagem, "all")

    strategy = ElevenNumbersStrategy()
    pred = strategy.predict(draws, approach=engine_approach)

    dezenas_str = "  ".join(f"{n:02d}" for n in sorted(pred.dezenas))
    console.print()
    console.print(Panel(
        f"[bold cyan]Predição — Concurso {pred.concurso_alvo}[/bold cyan]\n\n"
        f"[yellow]{dezenas_str}[/yellow]\n\n"
        f"Abordagem: [dim]{pred.abordagem}[/dim]\n"
        f"Confiança: [green]{pred.confianca_media:.4f}[/green]",
        box=box.DOUBLE_EDGE,
    ))

    approach_tag = abordagem.replace("todas", "ensemble")

    _saida = SAIDA_DIR / "jogos"
    _saida.mkdir(parents=True, exist_ok=True)
    out = _saida / f"predicao_{approach_tag}_{pred.concurso_alvo}.json"
    out.write_text(
        json.dumps({
            "concurso": pred.concurso_alvo,
            "abordagem": approach_tag,
            "dezenas": sorted(pred.dezenas),
            "confianca": round(pred.confianca_media, 4),
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    console.print(f"  [dim]💾 Salvo em saida/jogos/predicao_{approach_tag}_{pred.concurso_alvo}.json[/dim]")


def _register_subapps() -> None:
    from lotofacil.interface.cli.dados import app as dados_app
    from lotofacil.interface.cli.modelo import app as modelo_app
    from lotofacil.interface.cli.portfolio import app as portfolio_app
    from lotofacil.interface.cli.lab import app as lab_app

    app.add_typer(dados_app, name="dados")
    app.add_typer(modelo_app, name="modelo")
    app.add_typer(portfolio_app, name="portfolio")
    app.add_typer(lab_app, name="lab", help="Pipeline experimental — clima, lua, ablação.")


_register_subapps()

if __name__ == "__main__":
    app()
