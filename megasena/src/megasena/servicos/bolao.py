"""Avaliação de bolão da Mega-Sena.

Segue `docs/guias/avaliacao-de-boloes.md`: todo volante vira
combinações simples equivalentes, o custo oficial sai delas, e o valor cobrado
é comparado com o teto de 35% de taxa de serviço permitido às lotéricas.
"""
from __future__ import annotations

from math import comb

from megasena.dominio.regras import (
    NUMEROS_POR_SORTEIO,
    PRECO_APOSTA_SIMPLES,
    TOTAL_NUMEROS,
    combinacoes_por_aposta,
)

TAXA_MAXIMA_LOTERICA = 0.35
FAIXAS = {6: "sena", 5: "quina", 4: "quadra"}


def _prob_acertos_no_volante(dezenas: int, acertos: int) -> float:
    """P(exatamente `acertos` das 6 sorteadas estarem num volante de `dezenas`)."""
    return (
        comb(dezenas, acertos)
        * comb(TOTAL_NUMEROS - dezenas, NUMEROS_POR_SORTEIO - acertos)
        / comb(TOTAL_NUMEROS, NUMEROS_POR_SORTEIO)
    )


def _pct(x: float) -> str:
    return f"{x:.1%}".replace(".", ",")


def _um_em(p: float) -> int | None:
    return round(1 / p) if p > 0 else None


def avaliar_bolao(
    valor_total: float, apostas: int, dezenas: int, cotas: int | None = None,
) -> dict:
    """Avalia preço e probabilidade de um bolão.

    `valor_total` é a soma de todas as cotas vendidas (valor da cota × número
    de cotas). `cotas`, se informado, só serve para mostrar os valores por cota.
    """
    if valor_total <= 0:
        raise ValueError("valor_total deve ser maior que zero")
    if apostas < 1:
        raise ValueError("apostas deve ser pelo menos 1")
    if cotas is not None and cotas < 1:
        raise ValueError("cotas deve ser pelo menos 1")

    comb_por_aposta = combinacoes_por_aposta(dezenas)
    combinacoes = apostas * comb_por_aposta
    custo_oficial = round(combinacoes * PRECO_APOSTA_SIMPLES, 2)
    teto_comercial = round(custo_oficial * (1 + TAXA_MAXIMA_LOTERICA), 2)
    taxa = valor_total / custo_oficial - 1

    if taxa > TAXA_MAXIMA_LOTERICA + 1e-9:
        veredito = "sobrepreco"
        mensagem = (
            f"Taxa de {_pct(taxa)} acima do limite de {TAXA_MAXIMA_LOTERICA:.0%}: "
            "o bolão está caro demais e não compensa."
        )
    elif taxa < -1e-9:
        veredito = "abaixo_do_custo"
        mensagem = (
            "Valor cobrado abaixo do custo oficial das apostas. Bom para você se "
            "for verdade — confira nos bilhetes se as apostas existem como informado."
        )
    else:
        veredito = "aceitavel"
        mensagem = (
            f"Taxa de {_pct(taxa)}, dentro do limite de {TAXA_MAXIMA_LOTERICA:.0%} "
            "das lotéricas: preço aceitável."
        )

    # Sena: combinações distintas não se sobrepõem, então a soma é exata
    # (assumindo que o bolão não repete jogos).
    total = comb(TOTAL_NUMEROS, NUMEROS_POR_SORTEIO)
    p_sena = min(combinacoes / total, 1.0)

    # Quina/quadra: probabilidade por volante. Volantes diferentes não são
    # independentes, então não somamos — mostramos o número por bilhete.
    por_volante = {
        nome: {
            "probabilidade": _prob_acertos_no_volante(dezenas, k),
            "um_em": _um_em(_prob_acertos_no_volante(dezenas, k)),
        }
        for k, nome in FAIXAS.items()
    }

    resultado = {
        "entrada": {"valor_total": valor_total, "apostas": apostas, "dezenas": dezenas, "cotas": cotas},
        "combinacoes_por_aposta": comb_por_aposta,
        "combinacoes_total": combinacoes,
        "custo_oficial": custo_oficial,
        "teto_comercial": teto_comercial,
        "taxa_cobrada": taxa,
        "taxa_maxima": TAXA_MAXIMA_LOTERICA,
        "veredito": veredito,
        "mensagem": mensagem,
        "sena": {"probabilidade": p_sena, "um_em": _um_em(p_sena)},
        "por_volante": por_volante,
        "custo_por_combinacao_cobrado": round(valor_total / combinacoes, 2),
    }
    if cotas:
        resultado["por_cota"] = {
            "cobrado": round(valor_total / cotas, 2),
            "justo_sem_taxa": round(custo_oficial / cotas, 2),
            "maximo_com_taxa": round(teto_comercial / cotas, 2),
        }
    return resultado


def comparar_boloes(boloes: list[dict]) -> dict:
    """Ordena bolões do melhor para o pior custo-benefício para quem compra uma cota.

    Quem compra 1 de N cotas tem a chance de sena do bolão inteiro, mas leva
    1/N do prêmio. O prêmio esperado por real pago fica então proporcional a
    combinações / valor_total — o número de cotas se cancela. Por isso o
    critério é o **custo cobrado por combinação simples** (menor é melhor).
    Empate: mais dezenas por volante, que paga quinas/quadras em cascata
    quando a sena sai. Ver docs/guias/avaliacao-de-boloes.md, seção 7.

    Cada item de `boloes` tem as chaves de `avaliar_bolao` e, opcionalmente, `nome`.
    """
    if len(boloes) < 2:
        raise ValueError("informe pelo menos 2 bolões para comparar")

    itens = []
    for i, b in enumerate(boloes, start=1):
        cotas = b.get("cotas")
        avaliacao = avaliar_bolao(b["valor_total"], b["apostas"], b["dezenas"], cotas)
        valor_total = avaliacao["entrada"]["valor_total"]
        itens.append({
            "nome": b.get("nome") or f"Bolão {i}",
            "valor_cota": round(valor_total / cotas, 2) if cotas else round(valor_total, 2),
            "fracao_premio": 1 / cotas if cotas else 1.0,
            "custo_por_combinacao": valor_total / avaliacao["combinacoes_total"],
            "avaliacao": avaliacao,
        })

    itens.sort(key=lambda x: (
        round(x["custo_por_combinacao"], 6),
        -x["avaliacao"]["entrada"]["dezenas"],
        -x["avaliacao"]["combinacoes_total"],
    ))
    for posicao, item in enumerate(itens, start=1):
        item["posicao"] = posicao

    maior_chance = max(itens, key=lambda x: x["avaliacao"]["sena"]["probabilidade"])
    menor_cota = min(itens, key=lambda x: x["valor_cota"])
    return {
        "ranking": itens,
        "melhor": itens[0]["nome"],
        "destaques": {
            "custo_beneficio": itens[0]["nome"],
            "maior_chance": maior_chance["nome"],
            "menor_cota": menor_cota["nome"],
        },
    }
