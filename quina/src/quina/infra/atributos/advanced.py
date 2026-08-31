from __future__ import annotations

import logging
import math
from collections import Counter
from typing import Dict, List

from quina.dominio.entidades import Sorteio as Draw
from quina.infra.atributos.base import freq_k, atraso as calc_atraso

_NUMBERS = list(range(1, 81))
_FAIXAS = {
    1: range(1, 17),
    2: range(17, 33),
    3: range(33, 49),
    4: range(49, 65),
    5: range(65, 81),
}

logger = logging.getLogger(__name__)

# Abaixo deste esperado(n, m) medio, o lift e dominado por ruido de contagem
# inteira (passo minimo de 1/esperado) e nao por sinal estatistico real.
# Ver nota honesta em coocorrencia_score.
_ESPERADO_MINIMO_CONFIAVEL = 5.0

# `coocorrencia_score` e chamada uma vez por linha do dataset — milhares de
# vezes num treino. A condicao de esperado-baixo depende so de (k, top) e da
# densidade da loteria, nunca do idx, entao avisar a cada chamada emitiria
# ~2800 linhas identicas por treino: o aviso seria silenciado e ninguem o
# leria. Emitimos uma vez por combinacao de parametros, por processo.
_avisos_esperado_baixo: set[tuple[int, int]] = set()


def _avisar_esperado_baixo(k: int, top: int, media_esperado: float) -> None:
    if media_esperado >= _ESPERADO_MINIMO_CONFIAVEL:
        return
    chave = (k, top)
    if chave in _avisos_esperado_baixo:
        return
    _avisos_esperado_baixo.add(chave)
    logger.warning(
        "coocorrencia_score: esperado medio=%.2f (< %.0f) com k=%d, top=%d -- "
        "lift dominado por ruido de contagem, nao por dependencia real "
        "(ver NOTA HONESTA na docstring). Aviso emitido uma vez por processo.",
        media_esperado, _ESPERADO_MINIMO_CONFIAVEL, k, top,
    )




def coocorrencia_score(
    draws: List[Draw], idx: int, k: int = 50, top: int = 20, alpha: float = 1.0
) -> Dict[int, float]:
    """
    Afinidade de cada dezena com as `top` dezenas mais frequentes da janela `k`,
    medida via lift observado/esperado sobre independencia estatistica, com
    suavizacao aditiva (add-alpha / Laplace):

        lift(n, m) = (observado(n, m) + alpha) / (esperado(n, m) + alpha)
        esperado(n, m) = tamanho_da_janela * freq(n) * freq(m)

    O score de uma dezena N e a media dos lifts entre N e cada uma das `top`
    dezenas mais quentes da janela.

    NOTA HONESTA: o valor neutro sob independencia estatistica e 1.0 por
    construcao -- e por isso que "sem evidencia" (janela vazia, ou a dezena
    nunca saiu na janela) tambem retorna 1.0 aqui, nunca 0.0, que seria
    codificar "nunca vi essa dezena" como "maxima anti-afinidade". Mas o
    ESTIMADOR tem um vies negativo conhecido, medido, que nao desaparece so
    com suavizacao: com sorteios uniformes verdadeiramente independentes
    (k=50, top=20, 22400 amostras, seed=99), a media medida foi 0.957 (desvio
    de 0.043 abaixo de 1.0), nao exatamente 1.0. O vies vem de duas fontes:
    (1) desigualdade de Jensen -- E[obs/esp] < E[obs]/E[esp] quando `esp` e
    pequeno, como e o caso aqui (esta e a loteria mais esparsa das quatro:
    esperado(n,m) tipicamente bem menor que 1 numa janela de 50 concursos);
    (2) a propria suavizacao aditiva, que por definicao puxa para 1.0 mas nao
    anula o viés quando a evidencia e fraca. Nao trate 0.957 como "quase
    certo" nem invente uma correcao de vies sem reportar -- o numero fica ai
    porque foi medido, nao porque e o alvo.

    Em loterias esparsas (poucas dezenas sorteadas frente ao universo total,
    como e o caso daqui), `esperado(n, m)` costuma ser bem menor que 1 numa
    janela de dezenas de concursos. Como `observado` e uma contagem inteira,
    o lift bruto (sem suavizacao) so pode assumir multiplos de `1/esperado`
    -- um unico coocorrencia observado ja faz o lift saltar de 0 para varias
    unidades. A suavizacao com `alpha` (padrao 1.0) reduz esse viés pela
    metade nesta loteria (0.087 sem suavizacao -> 0.043 com suavizacao, no
    mesmo experimento), mas nao o elimina; ainda assim, com `esperado` muito
    baixo, nao espere um sinal fino -- espere algo perto de 1.0 quase sempre,
    com saltos discretos ocasionais. Um WARNING e emitido quando o esperado
    medio da janela fica abaixo de um limiar de confianca (ver
    `_ESPERADO_MINIMO_CONFIAVEL`); nao interprete valores altos como evidencia
    de "pares que saem juntos" mesmo quando o warning nao dispara.
    """
    window = draws[max(0, idx - k):idx]
    # 1.0 e o valor neutro sob independencia (ver NOTA HONESTA), nao 0.0:
    # "sem evidencia" (janela vazia, ou a dezena nunca saiu na janela) nao e
    # o mesmo que "maxima anti-afinidade".
    scores = {n: 1.0 for n in _NUMBERS}
    n_window = len(window)
    if n_window == 0:
        return scores

    freq = freq_k(draws, idx, k)
    top_dezenas = sorted(_NUMBERS, key=lambda n: freq[n], reverse=True)[:top]
    top_set = set(top_dezenas)

    # Conta pares apenas contra as `top` dezenas quentes (nao a matriz cheia
    # _NUMBERS x _NUMBERS), muito mais barato quando build_dataset chama esta
    # funcao uma vez por linha do dataset.
    pair_counts = {m: Counter() for m in top_dezenas}
    for d in window:
        dez_set = set(d.dezenas)
        hot_in_draw = dez_set & top_set
        if not hot_in_draw:
            continue
        for m in hot_in_draw:
            pair_counts[m].update(n for n in dez_set if n != m)

    esperados: List[float] = []
    for n in _NUMBERS:
        lifts = []
        for m in top_dezenas:
            if m == n or freq[n] <= 0 or freq[m] <= 0:
                continue
            esperado = n_window * freq[n] * freq[m]
            observado = pair_counts[m][n]
            lifts.append((observado + alpha) / (esperado + alpha))
            esperados.append(esperado)
        scores[n] = sum(lifts) / len(lifts) if lifts else 1.0

    if esperados:
        media_esperado = sum(esperados) / len(esperados)
        _avisar_esperado_baixo(k, top, media_esperado)

    return scores


def trend_score(draws: List[Draw], idx: int) -> Dict[int, float]:
    f10 = freq_k(draws, idx, k=10)
    f50 = freq_k(draws, idx, k=50)
    return {n: f10[n] - f50[n] for n in _NUMBERS}


def volatilidade_score(
    draws: List[Draw], idx: int, outer_k: int = 100, inner_k: int = 20
) -> Dict[int, float]:
    window = draws[max(0, idx - outer_k):idx]
    n_windows = max(1, len(window) // inner_k)
    scores = {n: [] for n in _NUMBERS}

    for w in range(n_windows):
        sub = window[w * inner_k:(w + 1) * inner_k]
        if not sub:
            continue
        counts = Counter()
        for d in sub:
            counts.update(d.dezenas)
        for n in _NUMBERS:
            scores[n].append(counts[n] / len(sub))

    result = {}
    for n in _NUMBERS:
        vals = scores[n]
        if len(vals) < 2:
            result[n] = 0.0
        else:
            mean = sum(vals) / len(vals)
            result[n] = math.sqrt(sum((v - mean) ** 2 for v in vals) / len(vals))
    return result


def faixa_dominante(draws: List[Draw], idx: int) -> int:
    if idx == 0:
        return 1
    dez = set(draws[idx - 1].dezenas)
    counts = {f: sum(1 for n in dez if n in rng) for f, rng in _FAIXAS.items()}
    return max(counts, key=counts.get)


def par_quente_score(draws: List[Draw], idx: int, k: int = 50) -> float:
    fk = freq_k(draws, idx, k=k)
    top20 = sorted(fk, key=fk.get, reverse=True)[:20]
    at = calc_atraso(draws, idx, max_atraso=50)
    return float(sum(1 for n in top20 if at[n] <= 5))