from quina.servicos.estrategias.frequencia_atraso import (
    gerar_candidato_frequencia_atraso,
    pontuar_por_frequencia_atraso,
)


def _draws_fixture():
    return [
        {"concurso": 1, "data": "01/01/2026", "dezenas": [1, 2, 3, 4, 5]},
        {"concurso": 2, "data": "02/01/2026", "dezenas": [1, 2, 6, 7, 8]},
        {"concurso": 3, "data": "03/01/2026", "dezenas": [1, 9, 10, 11, 12]},
    ]


class TestPontuarPorFrequenciaAtraso:
    def test_numero_mais_frequente_e_mais_recente(self):
        pontuacoes = pontuar_por_frequencia_atraso(_draws_fixture())
        # numero 1 saiu nos 3 concursos (freq maxima=3) e no ultimo concurso (atraso=0)
        assert pontuacoes[1] == 0.5

    def test_numero_nunca_sorteado_tem_atraso_maximo(self):
        pontuacoes = pontuar_por_frequencia_atraso(_draws_fixture())
        # numero 80 nunca saiu: freq=0 (norm 0.0), atraso=3=max_atraso (norm 1.0)
        assert pontuacoes[80] == 0.5

    def test_pesos_customizados_zeram_componente_de_atraso(self):
        pontuacoes = pontuar_por_frequencia_atraso(_draws_fixture(), peso_freq=1.0, peso_atraso=0.0)
        assert pontuacoes[80] == 0.0  # nunca sorteado, peso_atraso zerado


class TestGerarCandidatoFrequenciaAtraso:
    def test_tamanho_correto(self):
        candidato = gerar_candidato_frequencia_atraso(_draws_fixture(), tamanho_aposta=5)
        assert len(candidato["dezenas"]) == 5
        assert len(set(candidato["dezenas"])) == 5

    def test_numero_mais_frequente_esta_entre_os_escolhidos(self):
        candidato = gerar_candidato_frequencia_atraso(_draws_fixture(), tamanho_aposta=5)
        assert 1 in candidato["dezenas"]
