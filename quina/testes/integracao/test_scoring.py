from quina.servicos.estrategias import scoring


def _draws_fixture():
    return [
        {"concurso": 1, "data": "01/01/2026", "dezenas": [1, 2, 3, 4, 5]},
        {"concurso": 2, "data": "02/01/2026", "dezenas": [6, 7, 8, 9, 10]},
        {"concurso": 3, "data": "03/01/2026", "dezenas": [11, 12, 13, 14, 15]},
    ]


class TestGerarCandidatos:
    def test_gera_quantidade_correta(self):
        candidatos = scoring.gerar_candidatos(quantidade=20, tamanho_aposta=5, draws=_draws_fixture())
        assert len(candidatos) == 20

    def test_cada_candidato_tem_tamanho_correto_e_dezenas_validas(self):
        candidatos = scoring.gerar_candidatos(quantidade=10, tamanho_aposta=7, draws=_draws_fixture())
        for c in candidatos:
            assert len(c["dezenas"]) == 7
            assert len(set(c["dezenas"])) == 7
            assert all(1 <= d <= 80 for d in c["dezenas"])
            assert c["dezenas"] == sorted(c["dezenas"])

    def test_candidatos_ordenados_por_score_decrescente(self):
        candidatos = scoring.gerar_candidatos(quantidade=30, tamanho_aposta=5, draws=_draws_fixture())
        scores = [c["score"] for c in candidatos]
        assert scores == sorted(scores, reverse=True)

    def test_score_entre_zero_e_um(self):
        candidatos = scoring.gerar_candidatos(quantidade=30, tamanho_aposta=5, draws=_draws_fixture())
        assert all(0.0 <= c["score"] <= 1.0 for c in candidatos)

    def test_detalhes_tem_todos_os_filtros(self):
        candidatos = scoring.gerar_candidatos(quantidade=1, tamanho_aposta=5, draws=_draws_fixture())
        assert set(candidatos[0]["detalhes"].keys()) == set(scoring.FILTROS_PADRAO.keys())


class TestTopK:
    def test_retorna_k_melhores(self):
        candidatos = [
            {"dezenas": [1, 2, 3, 4, 5], "score": 0.5},
            {"dezenas": [6, 7, 8, 9, 10], "score": 0.9},
            {"dezenas": [11, 12, 13, 14, 15], "score": 0.1},
        ]
        top = scoring.top_k(candidatos, 2)
        assert [c["score"] for c in top] == [0.9, 0.5]
