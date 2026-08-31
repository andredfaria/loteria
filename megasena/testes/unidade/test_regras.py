from megasena.dominio.regras import (
    FAIXAS_ACERTOS,
    NUMEROS_POR_SORTEIO,
    TOTAL_NUMEROS,
    VALID_NUMBERS,
    validar_dezenas,
    contar_acertos,
    contar_pares,
    contar_impares,
    soma_dezenas,
    total_combinacoes,
)


def test_constantes():
    assert TOTAL_NUMEROS == 60
    assert NUMEROS_POR_SORTEIO == 6
    assert FAIXAS_ACERTOS == [4, 5, 6]
    assert len(VALID_NUMBERS) == 60


def test_validar_dezenas_valido():
    assert validar_dezenas([1, 2, 3, 4, 5, 6])


def test_validar_dezenas_quantidade_errada():
    assert not validar_dezenas([1, 2, 3, 4, 5])


def test_validar_dezenas_duplicadas():
    assert not validar_dezenas([1, 2, 3, 4, 5, 5])


def test_validar_dezenas_fora_range():
    assert not validar_dezenas([1, 2, 3, 4, 5, 61])


def test_contar_acertos():
    aposta = [1, 2, 3, 4, 5, 6]
    resultado = [1, 3, 5, 7, 9, 11]
    assert contar_acertos(aposta, resultado) == 3


def test_contar_acertos_zero():
    aposta = [1, 2, 3, 4, 5, 6]
    resultado = [7, 8, 9, 10, 11, 12]
    assert contar_acertos(aposta, resultado) == 0


def test_contar_pares():
    assert contar_pares([2, 4, 6, 8, 10, 12]) == 6
    assert contar_pares([1, 3, 5, 7, 9, 11]) == 0
    assert contar_pares([1, 2, 3, 4, 5, 6]) == 3


def test_contar_impares():
    assert contar_impares([1, 2, 3, 4, 5, 6]) == 3


def test_soma_dezenas():
    assert soma_dezenas([1, 2, 3, 4, 5, 6]) == 21


def test_total_combinacoes():
    assert total_combinacoes() == 50063860  # C(60,6)