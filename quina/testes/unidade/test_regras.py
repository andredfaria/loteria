from quina.dominio.regras import (
    FAIXAS_ACERTOS,
    NUMEROS_POR_SORTEIO,
    TAMANHO_APOSTA_MAX,
    TAMANHO_APOSTA_MIN,
    TOTAL_NUMEROS,
    VALID_NUMBERS,
    contar_acertos,
    contar_impares,
    contar_pares,
    custo_aposta,
    estatisticas_dezenas,
    gerar_combinacoes,
    repetidos_anterior,
    soma_dezenas,
    total_combinacoes,
    validar_dezenas,
)
import pytest


class TestConstantes:
    def test_total_numeros(self):
        assert TOTAL_NUMEROS == 80

    def test_numeros_por_sorteio(self):
        assert NUMEROS_POR_SORTEIO == 5

    def test_valid_numbers_range(self):
        assert VALID_NUMBERS == set(range(1, 81))

    def test_faixas_acertos(self):
        assert FAIXAS_ACERTOS == [2, 3, 4, 5]


class TestValidarDezenas:
    def test_valid(self):
        assert validar_dezenas([1, 2, 3, 4, 5]) is True

    def test_invalid_count_too_few(self):
        assert validar_dezenas([1, 2, 3, 4]) is False

    def test_invalid_count_too_many(self):
        assert validar_dezenas([1, 2, 3, 4, 5, 6]) is False

    def test_invalid_duplicates(self):
        assert validar_dezenas([1, 1, 2, 3, 4]) is False

    def test_invalid_out_of_range(self):
        assert validar_dezenas([1, 2, 3, 4, 81]) is False
        assert validar_dezenas([0, 2, 3, 4, 5]) is False


class TestContarAcertos:
    def test_full_match(self):
        assert contar_acertos([14, 15, 48, 58, 73], [14, 15, 48, 58, 73]) == 5

    def test_partial_match(self):
        assert contar_acertos([14, 15, 48, 58, 73], [14, 15, 1, 2, 3]) == 2

    def test_no_match(self):
        assert contar_acertos([1, 2, 3, 4, 5], [6, 7, 8, 9, 10]) == 0


class TestEstatisticas:
    def test_contar_pares_impares(self):
        assert contar_pares([14, 15, 48, 58, 73]) == 3
        assert contar_impares([14, 15, 48, 58, 73]) == 2

    def test_soma_dezenas(self):
        assert soma_dezenas([14, 15, 48, 58, 73]) == 208

    def test_repetidos_anterior(self):
        assert repetidos_anterior([14, 15, 48, 58, 73], [15, 42, 63, 66, 77]) == 1

    def test_estatisticas_dezenas(self):
        stats = estatisticas_dezenas([14, 15, 48, 58, 73])
        assert stats == {"pares": 3, "impares": 2, "soma": 208}


class TestCombinacoes:
    def test_total_combinacoes_default(self):
        assert total_combinacoes() == 24040016

    def test_gerar_combinacoes_count(self):
        combos = list(gerar_combinacoes(2))
        assert len(combos) == 3160


class TestCustoAposta:
    def test_aposta_minima_5_dezenas(self):
        assert custo_aposta(5) == 3.00

    def test_aposta_6_dezenas(self):
        assert custo_aposta(6) == 18.00  # comb(6,5)=6 * 3.00

    def test_aposta_maxima_15_dezenas(self):
        assert custo_aposta(15) == 9009.00  # comb(15,5)=3003 * 3.00

    def test_abaixo_do_minimo_levanta_erro(self):
        with pytest.raises(ValueError):
            custo_aposta(4)

    def test_acima_do_maximo_levanta_erro(self):
        with pytest.raises(ValueError):
            custo_aposta(16)

    def test_constantes(self):
        assert TAMANHO_APOSTA_MIN == 5
        assert TAMANHO_APOSTA_MAX == 15
