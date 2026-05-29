"""Tests for roi_lab service."""
import random
import pytest


def test_valida_filtros_sem_filtros_aceita_qualquer_jogo():
    from lotofacil.servicos.roi_lab import _valida_filtros
    nums = list(range(1, 16))
    assert _valida_filtros(nums, {}, None) is True


def test_valida_filtros_soma_fora_rejeita():
    from lotofacil.servicos.roi_lab import _valida_filtros
    # sum(1..15) = 120, fora de [171, 220]
    nums = list(range(1, 16))
    assert _valida_filtros(nums, {"soma": [171, 220]}, None) is False


def test_valida_filtros_soma_dentro_aceita():
    from lotofacil.servicos.roi_lab import _valida_filtros
    nums = [3, 5, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22]
    assert sum(nums) == 216
    assert _valida_filtros(nums, {"soma": [171, 220]}, None) is True


def test_valida_filtros_pares_fora_rejeita():
    from lotofacil.servicos.roi_lab import _valida_filtros
    # 12 pares: rejeita filtro [6,9]
    nums = [2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 1, 3, 5]
    pares = sum(1 for n in nums if n % 2 == 0)
    assert pares == 12
    assert _valida_filtros(nums, {"pares": [6, 9]}, None) is False


def test_valida_filtros_primos_dentro_aceita():
    from lotofacil.servicos.roi_lab import _valida_filtros, PRIMOS
    nums = list(range(1, 16))  # primos em 1-15: 2,3,5,7,11,13 = 6
    count = sum(1 for n in nums if n in PRIMOS)
    assert count == 6
    assert _valida_filtros(nums, {"primos": [4, 7]}, None) is True


def test_valida_filtros_repeticoes_sem_anterior_ignora():
    from lotofacil.servicos.roi_lab import _valida_filtros
    nums = list(range(1, 16))
    # sem anterior, filtro repeticoes é ignorado
    assert _valida_filtros(nums, {"repeticoes": [0, 0]}, None) is True


def test_valida_filtros_repeticoes_com_anterior():
    from lotofacil.servicos.roi_lab import _valida_filtros
    anterior = list(range(1, 16))  # 1-15
    # jogo com 8 números em comum com anterior
    nums = [1, 2, 3, 4, 5, 6, 7, 8, 17, 18, 19, 20, 21, 22, 23]
    assert len(set(nums) & set(anterior)) == 8
    assert _valida_filtros(nums, {"repeticoes": [8, 10]}, anterior) is True
    assert _valida_filtros(nums, {"repeticoes": [9, 10]}, anterior) is False


def test_valida_filtros_consecutivos():
    from lotofacil.servicos.roi_lab import _valida_filtros
    nums = [1, 2, 3, 4, 5, 10, 11, 15, 16, 17, 18, 19, 20, 21, 22]
    assert _valida_filtros(nums, {"consecutivos": 2}, None) is True
    assert _valida_filtros(nums, {"consecutivos": 20}, None) is False


def test_gerar_jogo_filtrado_retorna_15_numeros_validos():
    from lotofacil.servicos.roi_lab import _gerar_jogo_filtrado
    rng = random.Random(42)
    jogo = _gerar_jogo_filtrado({}, None, rng)
    assert jogo is not None
    assert len(jogo) == 15
    assert all(1 <= n <= 25 for n in jogo)
    assert len(set(jogo)) == 15


def test_gerar_jogo_filtrado_respeita_filtro_soma():
    from lotofacil.servicos.roi_lab import _gerar_jogo_filtrado, _valida_filtros
    rng = random.Random(42)
    filtros = {"soma": [171, 220]}
    for _ in range(10):
        jogo = _gerar_jogo_filtrado(filtros, None, rng)
        assert jogo is not None
        assert _valida_filtros(jogo, filtros, None) is True


def test_gerar_jogo_filtrado_impossivel_retorna_none():
    from lotofacil.servicos.roi_lab import _gerar_jogo_filtrado
    rng = random.Random(42)
    # soma > 300 é impossível (máximo é 25+24+...+11 = 270)
    jogo = _gerar_jogo_filtrado({"soma": [300, 400]}, None, rng)
    assert jogo is None
