import pytest
from pydantic import ValidationError

from quina.dominio.entidades import Sorteio, SorteioBruto
from quina.dominio.excecoes import BaseDesatualizada, QuinaError, SorteioNaoEncontrado


class TestSorteio:
    def test_valid(self):
        s = Sorteio(concurso=7059, data="07/07/2026", dezenas=[27, 47, 57, 70, 78])
        assert s.concurso == 7059
        assert len(s.dezenas) == 5

    def test_dezenas_sorted(self):
        s = Sorteio(concurso=7059, data="07/07/2026", dezenas=[78, 27, 70, 47, 57])
        assert s.dezenas == [27, 47, 57, 70, 78]

    def test_invalid_too_few(self):
        with pytest.raises(ValidationError):
            Sorteio(concurso=1, data="01/01/2026", dezenas=[1, 2, 3, 4])

    def test_invalid_too_many(self):
        with pytest.raises(ValidationError):
            Sorteio(concurso=1, data="01/01/2026", dezenas=[1, 2, 3, 4, 5, 6])

    def test_invalid_duplicates(self):
        with pytest.raises(ValidationError):
            Sorteio(concurso=1, data="01/01/2026", dezenas=[1, 1, 2, 3, 4])

    def test_invalid_out_of_range(self):
        with pytest.raises(ValidationError):
            Sorteio(concurso=1, data="01/01/2026", dezenas=[1, 2, 3, 4, 81])


class TestSorteioBruto:
    def test_valid(self):
        sb = SorteioBruto(
            concurso=7059,
            data="07/07/2026",
            dezenas=["27", "47", "57", "70", "78"],
            dezenasOrdemSorteio=["57", "78", "27", "70", "47"],
        )
        assert sb.concurso == 7059
        assert sb.dezenas == ["27", "47", "57", "70", "78"]


class TestExcecoes:
    def test_hierarchy(self):
        assert issubclass(SorteioNaoEncontrado, QuinaError)
        assert issubclass(BaseDesatualizada, QuinaError)
        assert issubclass(QuinaError, Exception)
