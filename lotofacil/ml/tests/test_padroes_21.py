import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from padroes_21 import calcular_score_padroes


def make_draw(concurso, dezenas):
    return {'concurso': concurso, 'dezenas': dezenas}


HISTORICO = [
    make_draw(1, list(range(1, 16))),   # 1-15
    make_draw(2, list(range(2, 17))),   # 2-16
    make_draw(3, list(range(3, 18))),   # 3-17
    make_draw(4, list(range(4, 19))),   # 4-18
    make_draw(5, list(range(5, 20))),   # 5-19  ← último draw
]


def test_retorna_25_elementos():
    scores = calcular_score_padroes(HISTORICO)
    assert len(scores) == 25


def test_scores_normalizados_entre_0_e_1():
    scores = calcular_score_padroes(HISTORICO)
    assert all(0.0 <= s <= 1.0 for s in scores)


def test_numero_no_ultimo_draw_tem_score_maior_que_ausente():
    scores = calcular_score_padroes(HISTORICO)
    assert scores[18] > scores[0]  # nº19 (último draw) > nº1 (ausente)


def test_numero_mais_frequente_tem_score_maior():
    scores = calcular_score_padroes(HISTORICO)
    assert scores[9] > scores[24]  # nº10 (todos os draws) > nº25 (nenhum)


def test_historico_vazio_retorna_zeros():
    scores = calcular_score_padroes([])
    assert scores == [0.0] * 25


def test_janela_respeita_parametro():
    scores_j2 = calcular_score_padroes(HISTORICO, janela=2)
    scores_j5 = calcular_score_padroes(HISTORICO, janela=5)
    assert scores_j2 != scores_j5


def test_numero_atrasado_tem_score_maior_que_zero():
    scores = calcular_score_padroes(HISTORICO)
    assert scores[24] >= 0.0


def test_historico_com_um_draw_funciona():
    scores = calcular_score_padroes([make_draw(1, list(range(1, 16)))])
    assert len(scores) == 25
    assert all(0.0 <= s <= 1.0 for s in scores)


def test_janela_zero_levanta_erro():
    with pytest.raises(ValueError):
        calcular_score_padroes(HISTORICO, janela=0)
