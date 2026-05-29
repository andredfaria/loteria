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
    holdout_pct: float = 0.0,
) -> dict[str, Any]:
    """Simula ROI histórico para os filtros dados vs. baseline aleatório.

    Returns:
        {
          "estrategia": FinancialResult dict,
          "baseline": FinancialResult dict,
          "meta": {total_sorteios, sorteios_treino, sorteios_teste, holdout_pct, concurso_corte}
        }
    """
    db = DatabaseManager()
    sorteios = db.get_all_concursos()
    if janela is not None:
        sorteios = sorteios[-janela:]

    total = len(sorteios)
    holdout_pct = max(0.0, min(holdout_pct, 0.9))
    n_teste = max(1, round(total * holdout_pct)) if holdout_pct > 0.0 else total
    sorteios_teste = sorteios[-n_teste:] if holdout_pct > 0.0 else sorteios
    concurso_corte = sorteios_teste[0]["concurso"] if sorteios_teste else None

    def _simular(filtros_ativos: dict[str, Any]) -> dict[str, Any]:
        rng = random.Random(42)
        resultados: list[dict] = []
        anterior: list[int] | None = None
        for sorteio in sorteios_teste:
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
        "meta": {
            "total_sorteios": total,
            "sorteios_treino": total - n_teste,
            "sorteios_teste": n_teste,
            "holdout_pct": holdout_pct,
            "concurso_corte": concurso_corte,
        },
    }


_PRESETS_AUTO_DISCOVER: list[dict[str, Any]] = [
    {"nome": "Baseline (aleatório)", "filtros": {}},
    {"nome": "Soma [171–220]", "filtros": {"soma": [171, 220]}},
    {"nome": "Soma + Pares [6–9]", "filtros": {"soma": [171, 220], "pares": [6, 9]}},
    {"nome": "Soma + Repetições [8–10]", "filtros": {"soma": [171, 220], "repeticoes": [8, 10]}},
    {"nome": "Soma + Consecutivos ≥2", "filtros": {"soma": [171, 220], "consecutivos": 2}},
    {"nome": "Soma + Pares + Repetições", "filtros": {"soma": [171, 220], "pares": [6, 9], "repeticoes": [8, 10]}},
    {"nome": "Soma + Pares + Moldura [8–11]", "filtros": {"soma": [171, 220], "pares": [6, 9], "moldura": [8, 11]}},
    {"nome": "Todos os filtros", "filtros": {
        "soma": [171, 220], "pares": [6, 9], "primos": [4, 7],
        "fibonacci": [3, 5], "moldura": [8, 11], "repeticoes": [8, 10], "consecutivos": 2,
    }},
]


def auto_descobrir_roi(
    n_jogos_por_sorteio: int = 3,
    holdout_pct: float = 0.2,
) -> dict[str, Any]:
    """Roda backtest para presets de filtros predefinidos e retorna ranking por ROI%.

    Returns:
        {"resultados": [{"nome", "filtros", "roi_pct", "sharpe", "rate_ge_13", "max_drawdown"}, ...],
         "meta": {total_sorteios, sorteios_teste, holdout_pct}}
    """
    db = DatabaseManager()
    sorteios = db.get_all_concursos()
    total = len(sorteios)
    holdout_pct = max(0.05, min(holdout_pct, 0.5))
    n_teste = max(1, round(total * holdout_pct))
    sorteios_teste = sorteios[-n_teste:]
    concurso_corte = sorteios_teste[0]["concurso"] if sorteios_teste else None

    def _simular_preset(filtros: dict[str, Any]) -> dict[str, Any]:
        rng = random.Random(42)
        resultados: list[dict] = []
        anterior: list[int] | None = None
        for sorteio in sorteios_teste:
            dezenas_reais = sorteio["dezenas"]
            for _ in range(n_jogos_por_sorteio):
                jogo = _gerar_jogo_filtrado(filtros, anterior, rng)
                resultados.append({"hits": len(set(jogo) & set(dezenas_reais)) if jogo else 0})
            anterior = dezenas_reais
        return dataclasses.asdict(FinancialSimulator().simulate(resultados))

    resultados_ranking = []
    for preset in _PRESETS_AUTO_DISCOVER:
        r = _simular_preset(preset["filtros"])
        resultados_ranking.append({
            "nome": preset["nome"],
            "filtros": preset["filtros"],
            "roi_pct": r["roi_pct"],
            "sharpe": r["sharpe"],
            "rate_ge_13": r["rate_ge"].get(13, 0),
            "max_drawdown": r["max_drawdown"],
            "n_games": r["n_games"],
        })

    resultados_ranking.sort(key=lambda x: x["roi_pct"], reverse=True)
    return {
        "resultados": resultados_ranking,
        "meta": {
            "total_sorteios": total,
            "sorteios_teste": n_teste,
            "holdout_pct": holdout_pct,
            "concurso_corte": concurso_corte,
            "n_jogos_por_sorteio": n_jogos_por_sorteio,
        },
    }
