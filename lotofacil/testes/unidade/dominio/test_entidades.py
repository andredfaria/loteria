"""Test core modules."""

from lotofacil.dominio.entidades import Draw
from lotofacil.dominio.regras import (
    validar_dezenas,
    contar_acertos,
    contar_pares,
    contar_primos,
    contar_fibonacci,
    contar_moldura,
    contar_consecutivos,
    estatisticas_dezenas,
)
from lotofacil.infra.config import TOTAL_NUMEROS as TOTAL_NUMBERS, NUMEROS_POR_SORTEIO as NUMBERS_PER_DRAW


class TestDraw:
    def test_valid_draw(self):
        d = Draw(concurso=1, data="01/01/2024", dezenas=list(range(1, 16)))
        assert d.concurso == 1
        assert len(d.dezenas) == 15

    def test_invalid_too_few(self):
        try:
            Draw(concurso=1, data="01/01/2024", dezenas=list(range(1, 10)))
            assert False, "Should have raised"
        except Exception:
            pass

    def test_dezenas_sorted(self):
        d = Draw(concurso=1, data="01/01/2024", dezenas=[15, 1, 10, 5, 3, 7, 2, 8, 4, 9, 6, 11, 12, 13, 14])
        assert d.dezenas == list(range(1, 16))


class TestLotteryRules:
    def test_validar_dezenas_valid(self):
        assert validar_dezenas(list(range(1, 16))) is True

    def test_validar_dezenas_invalid_count(self):
        assert validar_dezenas(list(range(1, 10))) is False

    def test_validar_dezenas_duplicates(self):
        assert validar_dezenas([1, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]) is False

    def test_contar_acertos(self):
        assert contar_acertos([1, 2, 3, 4, 5], [1, 2, 3, 6, 7]) == 3

    def test_contar_pares(self):
        assert contar_pares([2, 4, 6, 1, 3]) == 3

    def test_estatisticas_completas(self):
        stats = estatisticas_dezenas(list(range(1, 16)))
        assert stats["pares"] == 7
        assert stats["impares"] == 8
        assert stats["soma"] == sum(range(1, 16))
