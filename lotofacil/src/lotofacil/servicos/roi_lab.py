"""ROI Lab: statistical filter backtest service."""
from __future__ import annotations

import dataclasses
import random
from typing import Any

from lotofacil.dominio.regras import FIBONACCI, MOLDURA, PRIMOS
from lotofacil.infra.avaliacao.financeiro import FinancialSimulator
from lotofacil.infra.dados.banco import DatabaseManager

_TODOS_NUMEROS: list[int] = list(range(1, 26))
_MAX_TENTATIVAS: int = 200


def _valida_filtros(
    numeros: list[int],
    filtros: dict[str, Any],
    anterior: list[int] | None,
) -> bool:
    soma = sum(numeros)
    if (f := filtros.get("soma")) is not None and not (f[0] <= soma <= f[1]):
        return False

    pares = sum(1 for n in numeros if n % 2 == 0)
    if (f := filtros.get("pares")) is not None and not (f[0] <= pares <= f[1]):
        return False

    primos = sum(1 for n in numeros if n in PRIMOS)
    if (f := filtros.get("primos")) is not None and not (f[0] <= primos <= f[1]):
        return False

    fibs = sum(1 for n in numeros if n in FIBONACCI)
    if (f := filtros.get("fibonacci")) is not None and not (f[0] <= fibs <= f[1]):
        return False

    moldura = sum(1 for n in numeros if n in MOLDURA)
    if (f := filtros.get("moldura")) is not None and not (f[0] <= moldura <= f[1]):
        return False

    if anterior is not None and (f := filtros.get("repeticoes")) is not None:
        rep = len(set(numeros) & set(anterior))
        if not (f[0] <= rep <= f[1]):
            return False

    if (f := filtros.get("consecutivos")) is not None:
        s = sorted(numeros)
        consec = sum(1 for i in range(len(s) - 1) if s[i + 1] - s[i] == 1)
        if consec < f:
            return False

    return True


def _gerar_jogo_filtrado(
    filtros: dict[str, Any],
    anterior: list[int] | None,
    rng: random.Random,
) -> list[int] | None:
    for _ in range(_MAX_TENTATIVAS):
        candidato = sorted(rng.sample(_TODOS_NUMEROS, 15))
        if _valida_filtros(candidato, filtros, anterior):
            return candidato
    return None


def rodar_backtest_roi(
    filtros: dict[str, Any],
    n_jogos_por_sorteio: int = 5,
    janela: int | None = None,
) -> dict[str, Any]:
    """Simula ROI histórico para os filtros dados vs. baseline aleatório.

    Returns:
        {"estrategia": FinancialResult dict, "baseline": FinancialResult dict}
    """
    db = DatabaseManager()
    sorteios = db.get_all_concursos()  # [{concurso, data, dezenas}] ordenado por concurso
    if janela is not None:
        sorteios = sorteios[-janela:]

    def _simular(filtros_ativos: dict[str, Any]) -> dict[str, Any]:
        rng = random.Random(42)
        resultados: list[dict] = []
        anterior: list[int] | None = None
        for sorteio in sorteios:
            dezenas_reais = sorteio["dezenas"]
            for _ in range(n_jogos_por_sorteio):
                jogo = _gerar_jogo_filtrado(filtros_ativos, anterior, rng)
                if jogo is None:
                    resultados.append({"hits": 0})
                else:
                    hits = len(set(jogo) & set(dezenas_reais))
                    resultados.append({"hits": hits})
            anterior = dezenas_reais
        sim = FinancialSimulator()
        return dataclasses.asdict(sim.simulate(resultados))

    return {
        "estrategia": _simular(filtros),
        "baseline": _simular({}),
    }
