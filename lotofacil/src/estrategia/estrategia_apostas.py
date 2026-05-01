#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
src/estrategia/estrategia_apostas.py — Módulo de estratégia de apostas para Lotofácil

Calcula custo, ROI esperado e decide quantidade de jogos por carteira com base em
orçamento disponível e métricas do backtest/inferência ML.
"""

import json
import argparse
from pathlib import Path
from typing import Dict, Optional

_ROOT = Path(__file__).resolve().parent.parent.parent

CUSTO_POR_JOGO = 3.50  # BRL

ALOCACAO_PADRAO = {
    "conservadora": 3,   # Carteira A
    "balanceada":   3,   # Carteira B
    "agressiva":    2,   # Carteira C
    "antipadrao":   1,   # Carteira D
    "ml":           1,   # Carteira E
}  # Total: 10 jogos = R$25,00/concurso

PREMIOS_APROXIMADOS = {  # BRL (referência conservadora)
    15: 0,       # Jackpot variável — ignorado no cálculo
    14: 1700.0,
    13: 25.0,
    12: 10.0,
    11: 5.0,
}

# Probabilidades históricas aproximadas para Lotofácil (por jogo)
PROB_POR_ACERTO = {
    15: 1 / 3_268_760,
    14: 1 / 21_791,
    13: 1 / 691,
    12: 1 / 55,
    11: 1 / 10,
}


def calcular_custo_total(n_jogos: int, custo_por_jogo: float = CUSTO_POR_JOGO) -> float:
    return n_jogos * custo_por_jogo


def calcular_roi_esperado(
    n_jogos: int,
    p_11: float,
    p_12: float,
    p_13: float,
    p_14: float,
) -> Dict:
    """
    Retorna {"custo": float, "retorno_esperado": float, "roi_pct": float}.
    """
    custo = calcular_custo_total(n_jogos)

    # Retorno esperado por jogo: E[R] = sum(P(k) * premio(k))
    retorno_por_jogo = (
        p_11 * PREMIOS_APROXIMADOS[11] +
        p_12 * PREMIOS_APROXIMADOS[12] +
        p_13 * PREMIOS_APROXIMADOS[13] +
        p_14 * PREMIOS_APROXIMADOS[14]
    )
    retorno_total = retorno_por_jogo * n_jogos
    roi_pct = ((retorno_total - custo) / custo * 100) if custo > 0 else 0.0

    return {
        "custo": custo,
        "retorno_esperado": round(retorno_total, 2),
        "roi_pct": round(roi_pct, 2),
    }


def decidir_quantidade_jogos(
    orcamento: float,
    confianca_ml: float,
    backtest_ganho_pct: float,
) -> Dict[str, int]:
    """
    Regras:
    - orcamento < 25.0: usar alocação mínima (10 jogos)
    - 25 <= orcamento <= 50: usar ALOCACAO_PADRAO
    - orcamento > 50 e confianca_ml > 0.8: +2 jogos na carteira E (ML)
    - backtest_ganho_pct > 5.0: +1 agressiva, +1 ml
    Nunca ultrapassa orcamento / CUSTO_POR_JOGO total.
    """
    alocacao = dict(ALOCACAO_PADRAO)
    max_jogos = int(orcamento / CUSTO_POR_JOGO)

    if orcamento >= 50 and confianca_ml > 0.8:
        alocacao["ml"] += 2

    if backtest_ganho_pct > 5.0:
        alocacao["agressiva"] += 1
        alocacao["ml"] += 1

    # Garantir que não ultrapassa o orçamento
    while sum(alocacao.values()) > max_jogos and sum(alocacao.values()) > 0:
        # Remover da carteira menos prioritária
        for carteira in ["ml", "agressiva", "antipadrao", "balanceada", "conservadora"]:
            if alocacao[carteira] > 0:
                alocacao[carteira] -= 1
                break

    return alocacao


def carregar_backtest_stats(
    backtest_path: str = None,
) -> Dict:
    """
    Lê relatorio_backtest.json. Retorna defaults conservadores se não encontrado.
    """
    if backtest_path is None:
        backtest_path = str(_ROOT / "ml" / "relatorio_backtest.json")

    defaults = {
        "ganho_relativo_pct": 0.0,
        "ml_mean_hits": 8.9,
        "baseline_mean_hits": 8.9,
    }

    try:
        with open(backtest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        summary = data.get("summary", {})
        ml_stats = data.get("ml_stats", {}).get("mean_hits", {})
        base_stats = data.get("baseline_stats", {}).get("mean_hits", {})
        return {
            "ganho_relativo_pct": summary.get("ganho_relativo_mean_hits_pct", 0.0),
            "ml_mean_hits": ml_stats.get("mean", 8.9),
            "baseline_mean_hits": base_stats.get("mean", 8.9),
        }
    except Exception:
        return defaults


def gerar_plano_apostas(
    orcamento: float,
    concurso_alvo: int,
    backtest_path: str = None,
    recomendacao_ml_path: str = None,
) -> Dict:
    """
    Retorna plano completo de apostas.
    """
    backtest = carregar_backtest_stats(backtest_path)
    ganho_pct = backtest["ganho_relativo_pct"]

    # Confiança ML: normalizada entre 0 e 1 com base no ganho relativo
    confianca_ml = min(1.0, max(0.0, ganho_pct / 10.0))

    # Carregar score ML se disponível
    score_ml = backtest["ml_mean_hits"]
    if recomendacao_ml_path:
        try:
            with open(recomendacao_ml_path, "r", encoding="utf-8") as f:
                rec = json.load(f)
            score_ml = rec.get("expected_score", {}).get("mean_hits", score_ml)
        except Exception:
            pass

    alocacao = decidir_quantidade_jogos(orcamento, confianca_ml, ganho_pct)
    total_jogos = sum(alocacao.values())
    custo_total = calcular_custo_total(total_jogos)

    # ROI esperado baseado em P(>=11) histórica simplificada
    roi = calcular_roi_esperado(
        total_jogos,
        p_11=PROB_POR_ACERTO[11],
        p_12=PROB_POR_ACERTO[12],
        p_13=PROB_POR_ACERTO[13],
        p_14=PROB_POR_ACERTO[14],
    )

    recomendacao = "JOGAR" if custo_total <= orcamento else "AGUARDAR"

    if recomendacao == "JOGAR":
        justificativa = (
            f"Orçamento suficiente (R${orcamento:.2f}) para {total_jogos} jogos "
            f"(R${custo_total:.2f}). "
            f"Ganho ML vs Baseline: {ganho_pct:+.2f}%."
        )
    else:
        justificativa = (
            f"Orçamento insuficiente: {total_jogos} jogos custam R${custo_total:.2f} "
            f"mas orçamento é R${orcamento:.2f}."
        )

    return {
        "concurso_alvo": concurso_alvo,
        "alocacao": alocacao,
        "total_jogos": total_jogos,
        "custo_total": custo_total,
        "orcamento": orcamento,
        "sobra": round(orcamento - custo_total, 2),
        "roi_esperado": roi,
        "recomendacao_estrategia": recomendacao,
        "justificativa": justificativa,
        "ml_score_esperado": round(score_ml, 4),
        "backtest_ganho_pct": round(ganho_pct, 4),
    }


def imprimir_plano(plano: Dict):
    """Pretty-print tabular do plano de apostas."""
    print("=" * 60)
    print(f"PLANO DE APOSTAS — Concurso {plano['concurso_alvo']}")
    print("=" * 60)
    print(f"\nOrçamento disponível:  R$ {plano['orcamento']:.2f}")
    print(f"Custo total:           R$ {plano['custo_total']:.2f}")
    print(f"Sobra:                 R$ {plano['sobra']:.2f}")
    print(f"\nALOCAÇÃO DE JOGOS:")
    nomes = {
        "conservadora": "A - Conservadora",
        "balanceada":   "B - Balanceada",
        "agressiva":    "C - Agressiva",
        "antipadrao":   "D - Anti-padrão",
        "ml":           "E - ML Otimizada",
    }
    for chave, nome in nomes.items():
        n = plano["alocacao"].get(chave, 0)
        custo = n * CUSTO_POR_JOGO
        print(f"  Carteira {nome}: {n:2d} jogo(s) = R$ {custo:.2f}")
    print(f"  {'TOTAL':30s}: {plano['total_jogos']:2d} jogo(s) = R$ {plano['custo_total']:.2f}")

    roi = plano["roi_esperado"]
    print(f"\nROI ESPERADO (probabilístico):")
    print(f"  Retorno esperado: R$ {roi['retorno_esperado']:.4f}")
    print(f"  ROI:              {roi['roi_pct']:.2f}%")
    print(f"  (ROI negativo é esperado — loteria não é investimento)")

    print(f"\nML: score esperado = {plano['ml_score_esperado']:.4f} acertos")
    print(f"    ganho vs baseline = {plano['backtest_ganho_pct']:+.2f}%")

    print(f"\nRECOMENDAÇÃO: {plano['recomendacao_estrategia']}")
    print(f"  {plano['justificativa']}")
    print()
    print("AVISO: Loteria é jogo de azar. Não há método garantido de ganho.")
    print("       Jogue com responsabilidade e dentro do seu orçamento.")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Estratégia de apostas Lotofácil")
    parser.add_argument("--orcamento", type=float, required=True,
                        help="Orçamento disponível em BRL")
    parser.add_argument("--concurso", type=int, required=True,
                        help="Número do concurso alvo")
    parser.add_argument("--backtest",
                        default=str(_ROOT / "ml" / "relatorio_backtest.json"),
                        help="Caminho para relatorio_backtest.json")
    parser.add_argument("--ml-rec", default=None,
                        help="Caminho para recomendacao_concurso_N.json (opcional)")
    args = parser.parse_args()

    plano = gerar_plano_apostas(
        orcamento=args.orcamento,
        concurso_alvo=args.concurso,
        backtest_path=args.backtest,
        recomendacao_ml_path=args.ml_rec,
    )

    imprimir_plano(plano)


if __name__ == "__main__":
    main()
