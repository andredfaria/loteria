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


# ─── Comparação de bolões ──────────────────────────────────────

from megasena.servicos.bolao import comparar_boloes  # noqa: E402


def _bolao(nome, valor_total, apostas, dezenas, cotas=None):
    return {"nome": nome, "valor_total": valor_total, "apostas": apostas, "dezenas": dezenas, "cotas": cotas}


class TestCompararBoloes:
    def test_ranking_por_custo_por_combinacao(self):
        r = comparar_boloes([
            _bolao("caro", 567.0, 10, 7, 10),     # R$ 8,10 por combinação
            _bolao("justo", 420.0, 10, 7, 10),    # R$ 6,00 por combinação
            _bolao("medio", 500.0, 10, 7, 10),    # R$ 7,14 por combinação
        ])
        assert [b["nome"] for b in r["ranking"]] == ["justo", "medio", "caro"]
        assert [b["posicao"] for b in r["ranking"]] == [1, 2, 3]
        assert r["melhor"] == "justo"

    def test_bolao_maior_com_mais_chance_nao_vence_se_cobra_mais_por_combinacao(self):
        r = comparar_boloes([
            _bolao("grande", 2268.0, 10, 8, 20),  # 280 comb., R$ 8,10 cada
            _bolao("pequeno", 42.0, 1, 7, 5),     # 7 comb., R$ 6,00 cada
        ])
        assert r["melhor"] == "pequeno"
        assert r["destaques"]["maior_chance"] == "grande"
        assert r["destaques"]["custo_beneficio"] == "pequeno"

    def test_empate_de_custo_desempata_por_mais_dezenas_no_volante(self):
        # 28 jogos de 6 dezenas e 1 jogo de 8: mesmas 28 combinações, mesmo preço,
        # mas o volante de 8 paga quinas e quadras em cascata.
        r = comparar_boloes([
            _bolao("simples", 168.0, 28, 6),
            _bolao("ampliado", 168.0, 1, 8),
        ])
        assert r["melhor"] == "ampliado"

    def test_metricas_por_cota(self):
        r = comparar_boloes([
            _bolao("a", 567.0, 10, 7, 10),
            _bolao("b", 100.0, 1, 6),
        ])
        a = next(b for b in r["ranking"] if b["nome"] == "a")
        b = next(b for b in r["ranking"] if b["nome"] == "b")
        assert a["valor_cota"] == 56.7
        assert a["fracao_premio"] == pytest.approx(0.1)
        assert a["custo_por_combinacao"] == pytest.approx(8.1)
        assert a["avaliacao"]["veredito"] == "aceitavel"
        # Sem cotas, quem compra paga o bolão inteiro e leva o prêmio inteiro.
        assert b["valor_cota"] == 100.0
        assert b["fracao_premio"] == 1.0
        assert r["destaques"]["menor_cota"] == "a"

    def test_nome_padrao_pela_ordem_de_entrada(self):
        r = comparar_boloes([
            {"valor_total": 6.0, "apostas": 1, "dezenas": 6},
            {"valor_total": 7.0, "apostas": 1, "dezenas": 6},
        ])
        assert r["melhor"] == "Bolão 1"
        assert r["ranking"][1]["nome"] == "Bolão 2"

    def test_exige_pelo_menos_dois_boloes(self):
        with pytest.raises(ValueError):
            comparar_boloes([_bolao("so", 6.0, 1, 6)])
