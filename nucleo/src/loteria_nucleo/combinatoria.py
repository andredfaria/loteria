"""Cálculos comuns de combinações e probabilidades hipergeométricas."""
from __future__ import annotations

from math import comb

from loteria_nucleo.spec import LoteriaSpec


def _validar_dezenas(spec: LoteriaSpec, dezenas: int) -> None:
    if not spec.aposta_minima <= dezenas <= spec.aposta_maxima:
        raise ValueError(
            f"Tamanho de aposta deve estar entre {spec.aposta_minima} e "
            f"{spec.aposta_maxima}, recebido {dezenas}"
        )


def combinacoes_por_aposta(spec: LoteriaSpec, dezenas: int) -> int:
    _validar_dezenas(spec, dezenas)
    if spec.posicional:
        raise ValueError("Combinações genéricas não suportam loterias posicionais")
    return comb(dezenas, spec.numeros_por_sorteio)


def custo_aposta(spec: LoteriaSpec, dezenas: int) -> float:
    if spec.posicional:
        raise ValueError("Custo genérico não suporta loterias posicionais")
    if spec.preco_aposta_simples is None:
        raise ValueError(f"Preço simples não definido para {spec.nome}")
    return round(combinacoes_por_aposta(spec, dezenas) * spec.preco_aposta_simples, 2)


def total_combinacoes(spec: LoteriaSpec) -> int:
    if spec.posicional:
        return spec.total_numeros ** spec.numeros_por_sorteio
    return comb(spec.total_numeros, spec.numeros_por_sorteio)


def prob_acertos_no_volante(spec: LoteriaSpec, dezenas: int, acertos: int) -> float:
    _validar_dezenas(spec, dezenas)
    if spec.posicional:
        raise ValueError("Probabilidade genérica não suporta loterias posicionais")
    if acertos < 0 or acertos > spec.numeros_por_sorteio:
        raise ValueError("quantidade de acertos fora da faixa")
    restantes = spec.total_numeros - dezenas
    sorteados_fora = spec.numeros_por_sorteio - acertos
    if acertos > dezenas or sorteados_fora > restantes:
        return 0.0
    return (comb(dezenas, acertos) * comb(restantes, sorteados_fora)) / total_combinacoes(spec)
