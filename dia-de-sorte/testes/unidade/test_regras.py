from diadesorte.dominio.regras import (
    TODOS_MESES,
    TOTAL_NUMEROS,
    NUMEROS_POR_SORTEIO,
    VALID_NUMBERS,
    validar_dezenas,
    contar_acertos,
    contar_pares,
    contar_impares,
    soma_dezenas,
    mes_valido,
    total_combinacoes,
)


def test_constantes():
    assert TOTAL_NUMEROS == 31
    assert NUMEROS_POR_SORTEIO == 7
    assert len(TODOS_MESES) == 12
    assert len(VALID_NUMBERS) == 31


def test_validar_dezenas_valido():
    assert validar_dezenas([1, 2, 3, 4, 5, 6, 7])


def test_validar_dezenas_quantidade_errada():
    assert not validar_dezenas([1, 2, 3, 4, 5, 6])


def test_validar_dezenas_duplicadas():
    assert not validar_dezenas([1, 2, 3, 4, 5, 6, 6])


def test_validar_dezenas_fora_range():
    assert not validar_dezenas([1, 2, 3, 4, 5, 6, 32])


def test_contar_acertos():
    aposta = [1, 2, 3, 4, 5, 6, 7]
    resultado = [1, 3, 5, 7, 9, 11, 13]
    assert contar_acertos(aposta, resultado) == 4


def test_contar_acertos_zero():
    aposta = [1, 2, 3, 4, 5, 6, 7]
    resultado = [8, 9, 10, 11, 12, 13, 14]
    assert contar_acertos(aposta, resultado) == 0


def test_contar_pares():
    assert contar_pares([2, 4, 6, 8, 10, 12, 14]) == 7
    assert contar_pares([1, 3, 5, 7, 9, 11, 13]) == 0
    assert contar_pares([1, 2, 3, 4, 5, 6, 7]) == 3


def test_contar_impares():
    assert contar_impares([1, 2, 3, 4, 5, 6, 7]) == 4


def test_soma_dezenas():
    assert soma_dezenas([1, 2, 3, 4, 5, 6, 7]) == 28


def test_mes_valido():
    assert mes_valido("Janeiro")
    assert mes_valido("Dezembro")
    assert not mes_valido("Fevereiroo")
    assert not mes_valido("")


def test_total_combinacoes():
    assert total_combinacoes() == 2629575  # C(31,7)
