from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import numpy as np
from rich.console import Console
from rich.table import Table

from megasena.infra.config import DADOS_DIR
from megasena.infra.dados.leitor import load_draws
from megasena.infra.modelos.ensemble import EnsemblePredictor
from megasena.infra.geracao.optimizers import (
    NUMEROS,
    _check_filters,
    simulated_annealing,
)

console = Console()


def gerar_com_tatica(probas: np.ndarray, ultimo_dezenas, pool_size=12) -> dict:
    probas_dict = {n: float(probas[n - 1]) for n in NUMEROS}
    sorted_nums = sorted(NUMEROS, key=lambda n: probas_dict[n], reverse=True)
    pool = sorted_nums[:pool_size]
    numeros, score = simulated_annealing(probas=probas, pool=pool, ultimo_sorteio=ultimo_dezenas)
    checks = _check_filters(numeros, ultimo_dezenas)
    pares = sum(1 for n in numeros if n % 2 == 0)
    baixos = sum(1 for n in numeros if n <= 30)
    return {
        "numeros": sorted(numeros),
        "score": round(score * 100, 2),
        "filtros": checks,
        "pares": pares,
        "impares": 6 - pares,
        "baixos": baixos,
        "altos": 6 - baixos,
        "soma": sum(numeros),
        "probas": {n: round(probas_dict[n] * 100, 2) for n in sorted(numeros)},
    }


def main() -> None:
    draws = load_draws(DADOS_DIR)
    ultimo = draws[-1]
    console.print(f"[cyan]Último sorteio: Concurso {ultimo.concurso} ({ultimo.data})[/cyan]")
    console.print(f"  Dezenas: {' '.join(f'{n:02d}' for n in ultimo.dezenas)}\n")

    pred = EnsemblePredictor()
    pred.load()
    if not pred._fitted:
        console.print("[yellow]Treinando ensemble...[/yellow]")
        pred.fit(draws)
        pred.save()

    p_ml = pred.ml.predict_proba()
    p_freq = pred.frequency.predict_proba()
    p_prob = pred.probabilistic.predict_proba()
    p_emb = pred.predict_proba()

    def _comb(wf, wm, wp):
        return (wf * p_freq + wm * p_ml + wp * p_prob).astype(np.float32)

    taticas = [
        ("B — ML puro", p_ml, "somente classificador multioutput (RF+XGB+LGBM)"),
        ("C — Frequência pura", p_freq, "janelas de frequência (10/30/50/100/todo)"),
        ("D — Probabilístico", p_prob, "frequência recente + atraso (α=0.6/β=0.4)"),
        ("E — Ensemble pesado ML", _comb(0.0, 0.9, 0.1), "pesos freq=0 / ML=0.9 / prob=0.1"),
        ("F — Ensemble pesado Freq+Prob", _comb(0.5, 0.0, 0.5), "pesos freq=0.5 / ML=0 / prob=0.5"),
    ]

    base = gerar_com_tatica(p_emb, ultimo.dezenas)
    atual = set(base["numeros"])

    console.print(
        f"[bold]A — Ensemble padrão (atual):[/bold] {' '.join(f'{n:02d}' for n in base['numeros'])}"
        f"  (score {base['score']})"
    )

    table = Table(title=f"Jogos por tática de ML — Concurso {ultimo.concurso + 1}")
    table.add_column("Tática", style="cyan", no_wrap=True)
    table.add_column("Números", style="bold green")
    table.add_column("Score", justify="right")
    table.add_column("Par/Ímp", justify="center")
    table.add_column("Baixo/Alto", justify="center")
    table.add_column("Soma", justify="center")
    table.add_column("Repetição", justify="center")
    table.add_column("Int. c/ atual", justify="center")

    base_filtros = sum(1 for v in base["filtros"].values() if v)
    table.add_row(
        "A — Ensemble padrão",
        " ".join(f"{n:02d}" for n in base["numeros"]),
        f"{base['score']:.1f}",
        f"{base['pares']}/{base['impares']}",
        f"{base['baixos']}/{base['altos']}",
        str(base["soma"]),
        f"{len(atual & set(ultimo.dezenas))}",
        f"{base_filtros}/5 ✓",
    )

    for nome, probas, desc in taticas:
        j = gerar_com_tatica(probas, ultimo.dezenas)
        conjunto = set(j["numeros"])
        inter = len(atual & conjunto)
        filtros = sum(1 for v in j["filtros"].values() if v)
        table.add_row(
            nome,
            " ".join(f"{n:02d}" for n in j["numeros"]),
            f"{j['score']:.1f}",
            f"{j['pares']}/{j['impares']}",
            f"{j['baixos']}/{j['altos']}",
            str(j["soma"]),
            f"{len(conjunto & set(ultimo.dezenas))}",
            f"{inter}/6 · {filtros}/5 ✓",
        )

    console.print(table)

    console.print("\n[dim]Dica: táticas de ML com fontes de sinal diferentes raramente coincidem "
                  "em mais de 2 números — combine os números mais citados para diversificar. "
                  "Cada sorteio é independente; sem garantia de acerto.[/dim]")


if __name__ == "__main__":
    main()