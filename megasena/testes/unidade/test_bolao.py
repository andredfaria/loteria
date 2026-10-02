"""Avaliação de bolão — casos tirados de docs/guia_e_racional_de_avalia_o_de_bol_es.md."""
import pytest

from megasena.dominio.regras import combinacoes_por_aposta, custo_aposta
from megasena.servicos.bolao import avaliar_bolao


@pytest.mark.parametrize(
    "dezenas,combinacoes,custo",
    [(6, 1, 6.0), (7, 7, 42.0), (8, 28, 168.0), (9, 84, 504.0), (10, 210, 1260.0)],
)
def test_matriz_de_equivalencia_do_guia(dezenas, combinacoes, custo):
    assert combinacoes_por_aposta(dezenas) == combinacoes
    assert custo_aposta(dezenas) == custo


@pytest.mark.parametrize("dezenas", [5, 21])
def test_tamanho_fora_da_faixa(dezenas):
    with pytest.raises(ValueError):
        combinacoes_por_aposta(dezenas)


class TestCaso1DoGuia:
    """10 apostas de 7 dezenas, 10 cotas."""

    def test_no_teto_comercial_e_aceitavel(self):
        r = avaliar_bolao(567.0, apostas=10, dezenas=7, cotas=10)
        assert r["combinacoes_total"] == 70
        assert r["custo_oficial"] == 420.0
        assert r["teto_comercial"] == 567.0
        assert r["veredito"] == "aceitavel"
        assert r["sena"]["um_em"] == 715_198
        assert r["por_cota"] == {"cobrado": 56.7, "justo_sem_taxa": 42.0, "maximo_com_taxa": 56.7}

    def test_um_centavo_acima_do_teto_e_sobrepreco(self):
        r = avaliar_bolao(567.10, apostas=10, dezenas=7, cotas=10)
        assert r["veredito"] == "sobrepreco"

    def test_abaixo_do_custo_pede_conferencia(self):
        r = avaliar_bolao(400.0, apostas=10, dezenas=7)
        assert r["veredito"] == "abaixo_do_custo"
        assert "por_cota" not in r


def test_probabilidade_por_volante_bate_com_tabela_do_guia():
    r = avaliar_bolao(168.0, apostas=1, dezenas=8)
    assert r["por_volante"]["sena"]["um_em"] == 1_787_995
    assert r["sena"]["um_em"] == 1_787_995


def test_taxa_formatada_com_virgula():
    r = avaliar_bolao(500.0, apostas=10, dezenas=7)
    assert "19,0%" in r["mensagem"]


@pytest.mark.parametrize("kwargs", [
    {"valor_total": 0, "apostas": 1, "dezenas": 6},
    {"valor_total": 10, "apostas": 0, "dezenas": 6},
    {"valor_total": 10, "apostas": 1, "dezenas": 6, "cotas": 0},
])
def test_entradas_invalidas(kwargs):
    with pytest.raises(ValueError):
        avaliar_bolao(**kwargs)
