import pytest
from pydantic import ValidationError

from diadesorte.dominio.entidades import Sorteio


def test_sorteio_valido():
    s = Sorteio(concurso=1, data="01/01/2020", dezenas=[1, 2, 3, 4, 5, 6, 7], mes_sorte="Janeiro")
    assert s.concurso == 1
    assert s.dezenas == [1, 2, 3, 4, 5, 6, 7]
    assert s.mes_sorte == "Janeiro"


def test_sorteio_ordena_dezenas():
    s = Sorteio(concurso=1, data="01/01/2020", dezenas=[7, 6, 5, 4, 3, 2, 1])
    assert s.dezenas == [1, 2, 3, 4, 5, 6, 7]


def test_sorteio_mes_sorte_opcional():
    s = Sorteio(concurso=1, data="01/01/2020", dezenas=[1, 2, 3, 4, 5, 6, 7])
    assert s.mes_sorte == ""


def test_sorteio_quantidade_dezenas_invalida():
    with pytest.raises(ValidationError):
        Sorteio(concurso=1, data="01/01/2020", dezenas=[1, 2, 3, 4, 5, 6])


def test_sorteio_dezenas_duplicadas():
    with pytest.raises(ValidationError):
        Sorteio(concurso=1, data="01/01/2020", dezenas=[1, 2, 3, 4, 5, 6, 6])


def test_sorteio_dezenas_fora_range():
    with pytest.raises(ValidationError):
        Sorteio(concurso=1, data="01/01/2020", dezenas=[1, 2, 3, 4, 5, 6, 32])


def test_sorteio_dezenas_zeradas():
    with pytest.raises(ValidationError):
        Sorteio(concurso=1, data="01/01/2020", dezenas=[0, 1, 2, 3, 4, 5, 6])


def test_sorteio_mes_invalido():
    with pytest.raises(ValidationError):
        Sorteio(concurso=1, data="01/01/2020", dezenas=[1, 2, 3, 4, 5, 6, 7], mes_sorte="Foo")
