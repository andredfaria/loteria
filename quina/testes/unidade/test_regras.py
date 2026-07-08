from quina.dominio.regras import (
    FAIXAS_ACERTOS,
    NUMEROS_POR_SORTEIO,
    TOTAL_NUMEROS,
    VALID_NUMBERS,
    contar_acertos,
    contar_impares,
    contar_pares,
    estatisticas_dezenas,
    gerar_combinacoes,
    repetidos_anterior,
    soma_dezenas,
    total_combinacoes,
    validar_dezenas,
)


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
