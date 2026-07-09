"""Pontuação de dezenas por frequência e atraso históricos combinados."""
from __future__ import annotations

from quina.dominio.regras import TOTAL_NUMEROS


def pontuar_por_frequencia_atraso(
    draws: list[dict], peso_freq: float = 0.5, peso_atraso: float = 0.5
) -> dict[int, float]:
    frequencia = {n: 0 for n in range(1, TOTAL_NUMEROS + 1)}
    ultimo_indice: dict[int, int] = {}
    for i, sorteio in enumerate(draws):
        for n in sorteio["dezenas"]:
            frequencia[n] += 1
            ultimo_indice[n] = i

    total = len(draws)
    atraso = {
        n: (total - 1 - ultimo_indice[n]) if n in ultimo_indice else total
        for n in range(1, TOTAL_NUMEROS + 1)
    }

    max_freq = max(frequencia.values()) or 1
    max_atraso = max(atraso.values()) or 1

    return {
        n: round(
            peso_freq * (frequencia[n] / max_freq) + peso_atraso * (atraso[n] / max_atraso),
            4,
        )
        for n in range(1, TOTAL_NUMEROS + 1)
    }


def gerar_candidato_frequencia_atraso(
    draws: list[dict], tamanho_aposta: int, peso_freq: float = 0.5, peso_atraso: float = 0.5
) -> dict:
    pontuacoes = pontuar_por_frequencia_atraso(draws, peso_freq, peso_atraso)
    melhores = sorted(pontuacoes.items(), key=lambda kv: kv[1], reverse=True)[:tamanho_aposta]
    dezenas = sorted(n for n, _ in melhores)
    score = round(sum(p for _, p in melhores) / tamanho_aposta, 4)
    return {"dezenas": dezenas, "score": score}
