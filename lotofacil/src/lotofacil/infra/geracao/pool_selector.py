"""Seleção do pool de dezenas a fechar.

Ranqueia as 25 dezenas por um score composto de **frequência** (quão sorteada) e
**atraso** (concursos desde a última aparição), com override manual (fixar/excluir).

IMPORTANTE: isto é refino *marginal* de plausibilidade, **não previsão**. A Lotofácil
é um sorteio uniforme e independente; nenhum ranqueamento de dezenas melhora a chance
de acerto acima do acaso. O score só organiza um pool coerente para o fechamento.
"""
from __future__ import annotations

from typing import Sequence

from lotofacil.dominio.regras import TOTAL_NUMEROS

PESO_FREQUENCIA = 0.5
PESO_ATRASO = 0.5


def _scores(draws: Sequence) -> dict[int, float]:
    """Score composto [0,1] por dezena (frequência normalizada × atraso normalizado)."""
    total = len(draws)
    freq = {d: 0 for d in range(1, TOTAL_NUMEROS + 1)}
    ultima = {d: -1 for d in range(1, TOTAL_NUMEROS + 1)}
    for idx, draw in enumerate(draws):
        for d in draw.dezenas:
            freq[d] += 1
            ultima[d] = idx

    max_freq = max(freq.values()) or 1
    atraso = {d: (total - 1 - ultima[d]) if ultima[d] >= 0 else total for d in freq}
    max_atraso = max(atraso.values()) or 1

    return {
        d: PESO_FREQUENCIA * (freq[d] / max_freq) + PESO_ATRASO * (atraso[d] / max_atraso)
        for d in freq
    }


def selecionar_pool(
    draws: Sequence,
    n: int,
    fixar: Sequence[int] = (),
    excluir: Sequence[int] = (),
) -> list[int]:
    """Seleciona ``n`` dezenas para o pool de fechamento.

    ``fixar`` entram sempre; ``excluir`` nunca; o restante é preenchido pelos maiores
    scores. Retorna lista ordenada de ``n`` dezenas.
    """
    fixar_s, excluir_s = set(fixar), set(excluir)
    if not 15 <= n <= TOTAL_NUMEROS:
        raise ValueError(f"n deve estar entre 15 e {TOTAL_NUMEROS}")
    if fixar_s & excluir_s:
        raise ValueError("fixar e excluir não podem conter as mesmas dezenas")
    if len(fixar_s) > n:
        raise ValueError("fixar tem mais dezenas que o tamanho do pool")
    if not all(1 <= d <= TOTAL_NUMEROS for d in fixar_s | excluir_s):
        raise ValueError(f"dezenas devem estar entre 1 e {TOTAL_NUMEROS}")

    scores = _scores(draws)
    pool = set(fixar_s)
    # candidatos: maiores scores, excluindo os já fixados e os proibidos.
    # desempate determinístico pela própria dezena (ordem crescente).
    candidatos = sorted(
        (d for d in range(1, TOTAL_NUMEROS + 1) if d not in pool and d not in excluir_s),
        key=lambda d: (-scores[d], d),
    )
    for d in candidatos:
        if len(pool) >= n:
            break
        pool.add(d)

    if len(pool) < n:
        raise ValueError("dezenas insuficientes após excluir/fixar para formar o pool")
    return sorted(pool)
