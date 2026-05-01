"""Score de padrões dos últimos N draws para cada número 1-25."""
from __future__ import annotations
from typing import Dict, List


def calcular_score_padroes(historico: List[Dict], janela: int = 21) -> List[float]:
    """
    Calcula score de 5 padrões para cada número 1-25, normalizado para [0,1].
    historico: lista de concursos ordenada cronologicamente.
      Cada concurso: {'concurso': int, 'dezenas': List[int]} — dezenas devem ser inteiros.
      Use carregar_dados_historicos() para garantir o formato correto.
    Retorna lista de 25 floats (índice 0 = número 1, índice 24 = número 25).
    """
    if not historico:
        return [0.0] * 25

    if janela <= 0:
        raise ValueError(f"janela deve ser positivo, recebido: {janela}")

    ultimos = historico[-janela:] if len(historico) >= janela else historico
    n_draws = len(ultimos)
    ultimo_draw = set(ultimos[-1]['dezenas'])
    recentes3: set = set()
    for d in ultimos[-3:]:
        recentes3.update(d['dezenas'])

    scores = []
    for num in range(1, 26):
        freq_21 = sum(1 for d in ultimos if num in d['dezenas']) / n_draws

        repeticao = 1.0 if num in ultimo_draw else 0.0

        atraso_raw = n_draws
        for i, d in enumerate(reversed(ultimos)):
            if num in d['dezenas']:
                atraso_raw = i
                break
        # recência: menor atraso → maior score (1 = apareceu no último draw)
        atraso = 1.0 - min(atraso_raw / n_draws, 1.0)

        ciclo = 1.0 if num not in recentes3 else 0.0

        consecutivo = 0.0
        for viz in [num - 1, num + 1]:
            if 1 <= viz <= 25:
                freq_viz = sum(1 for d in ultimos if viz in d['dezenas']) / n_draws
                if freq_viz >= 0.6:
                    consecutivo = 1.0
                    break

        score = (
            0.30 * freq_21
            + 0.25 * repeticao
            + 0.20 * atraso
            + 0.15 * ciclo
            + 0.10 * consecutivo
        )
        scores.append(score)

    lo, hi = min(scores), max(scores)
    if hi > lo:
        return [(s - lo) / (hi - lo) for s in scores]
    return [0.5] * 25
