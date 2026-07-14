import pytest
from pydantic import ValidationError

from supersete.dominio.entidades import Sorteio


def test_sorteio_valido():
    s = Sorteio(concurso=1, data="01/01/2020", digitos=[0, 1, 2, 3, 4, 5, 6])
    assert s.concurso == 1
    assert s.digitos == [0, 1, 2, 3, 4, 5, 6]


def test_sorteio_mantem_ordem():
    s = Sorteio(concurso=1, data="01/01/2020", digitos=[9, 8, 7, 6, 5, 4, 3])
    assert s.digitos == [9, 8, 7, 6, 5, 4, 3]


def test_sorteio_quantidade_invalida():
    with pytest.raises(ValidationError):
        Sorteio(concurso=1, data="01/01/2020", digitos=[1, 2, 3, 4, 5, 6])


def test_sorteio_digito_fora_range():
    with pytest.raises(ValidationError):
        Sorteio(concurso=1, data="01/01/2020", digitos=[1, 2, 3, 4, 5, 6, 10])


def test_sorteio_digito_negativo():
    with pytest.raises(ValidationError):
        Sorteio(concurso=1, data="01/01/2020", digitos=[0, 1, 2, 3, 4, 5, -1])


def test_sorteio_todos_zero():
    s = Sorteio(concurso=1, data="01/01/2020", digitos=[0, 0, 0, 0, 0, 0, 0])
    assert s.digitos == [0, 0, 0, 0, 0, 0, 0]


def test_sorteio_todos_nove():
    s = Sorteio(concurso=1, data="01/01/2020", digitos=[9, 9, 9, 9, 9, 9, 9])
    assert s.digitos == [9, 9, 9, 9, 9, 9, 9]
