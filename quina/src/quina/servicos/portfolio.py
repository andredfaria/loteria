"""Geração de portfólio de jogos que respeita um orçamento informado."""
from __future__ import annotations

from quina.dominio.regras import custo_aposta
from quina.servicos.estrategias import scoring

PERFIS_TAMANHOS = {
    "conservador": [5],
    "equilibrado": [5, 6, 7, 8],
    "agressivo": [10, 12, 15],
}

_CANDIDATOS_POR_TAMANHO = 50


def gerar_portfolio(orcamento: float, perfil: str, draws: list[dict]) -> dict:
    if perfil not in PERFIS_TAMANHOS:
        raise ValueError(f"perfil desconhecido: {perfil}. Use um de: {', '.join(PERFIS_TAMANHOS)}")
    if orcamento <= 0:
        raise ValueError("orçamento deve ser maior que zero")

    candidatos = []
    for tamanho in PERFIS_TAMANHOS[perfil]:
        custo = custo_aposta(tamanho)
        if custo > orcamento:
            continue
        gerados = scoring.gerar_candidatos(quantidade=_CANDIDATOS_POR_TAMANHO, tamanho_aposta=tamanho, draws=draws)
        for candidato in gerados:
            candidatos.append({
                "dezenas": candidato["dezenas"],
                "score": candidato["score"],
                "tamanho_aposta": tamanho,
                "custo": custo,
            })

    candidatos.sort(key=lambda c: c["score"], reverse=True)

    jogos = []
    orcamento_restante = round(orcamento, 2)
    for candidato in candidatos:
        if candidato["custo"] <= orcamento_restante:
            jogos.append(candidato)
            orcamento_restante = round(orcamento_restante - candidato["custo"], 2)

    custo_total = round(orcamento - orcamento_restante, 2)
    return {"jogos": jogos, "custo_total": custo_total, "orcamento_sobra": orcamento_restante}
