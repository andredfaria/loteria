from supersete.dominio.regras import (
    NUM_COLUNAS,
    DIGITOS,
    TOTAL_COMBINACOES,
    VALOR_APOSTA,
    validar_digitos,
    contar_acertos,
    colunas_zeradas,
)


def test_constantes():
    assert NUM_COLUNAS == 7
    assert DIGITOS == set(range(10))
    assert TOTAL_COMBINACOES == 10_000_000
    assert VALOR_APOSTA == 2.50


def test_validar_digitos_valido():
    assert validar_digitos([0, 1, 2, 3, 4, 5, 6])


def test_validar_digitos_tamanho_errado():
    assert not validar_digitos([1, 2, 3, 4, 5, 6])


def test_validar_digitos_fora_range():
    assert not validar_digitos([0, 1, 2, 3, 4, 5, 10])


def test_validar_digitos_negativo():
    assert not validar_digitos([0, 1, 2, 3, 4, 5, -1])


def test_contar_acertos():
    assert contar_acertos([0, 1, 2, 3, 4, 5, 6], [0, 1, 2, 3, 4, 5, 6]) == 7


def test_contar_acertos_zero():
    assert contar_acertos([0, 0, 0, 0, 0, 0, 0], [1, 1, 1, 1, 1, 1, 1]) == 0


def test_contar_acertos_parcial():
    assert contar_acertos([0, 1, 2, 3, 4, 5, 6], [0, 9, 2, 9, 4, 9, 6]) == 4


def test_colunas_zeradas():
    assert colunas_zeradas([0, 1, 0, 3, 0, 5, 0]) == 4
    assert colunas_zeradas([1, 2, 3, 4, 5, 6, 7]) == 0
    assert colunas_zeradas([0, 0, 0, 0, 0, 0, 0]) == 7
