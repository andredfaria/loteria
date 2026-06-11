"""Testes do serviço de predição consolidada do próximo concurso."""

from __future__ import annotations

import json

import numpy as np
import pytest

from lotofacil.dominio.entidades import Predicao
from lotofacil.infra.estrategias.onze_dezenas.predictor import ElevenNumbersStrategy
from lotofacil.servicos.predicao_proximo_concurso import (
    BASELINE_ACERTOS_ESPERADO,
    gerar_predicao_proximo_concurso,
)


def _escrever_concurso(dados_dir, concurso, data, dezenas):
    path = dados_dir / f"concurso_{concurso}.json"
    path.write_text(json.dumps({"concurso": concurso, "data": data, "dezenas": dezenas}), encoding="utf-8")


@pytest.fixture
def dados_dir(tmp_path):
    # 3 concursos terminando numa sexta-feira (28/06/2024)
    _escrever_concurso(tmp_path, 100, "26/06/2024", list(range(1, 16)))
    _escrever_concurso(tmp_path, 101, "27/06/2024", list(range(2, 17)))
    _escrever_concurso(tmp_path, 102, "28/06/2024", list(range(3, 18)))
    return tmp_path


def _fake_prediction(concurso_alvo: int, abordagem: str = "ensemble") -> Predicao:
    probas = np.zeros(25)
    # Maiores probabilidades para 1..15
    for i in range(15):
        probas[i] = 1.0 - i * 0.01
    for i in range(15, 25):
        probas[i] = 0.1
    return Predicao(
        concurso_alvo=concurso_alvo,
        dezenas=list(range(1, 12)),
        probabilidades=probas.tolist(),
        confianca_media=0.5,
        estrategia="11-numbers",
        abordagem=abordagem,
    )


def test_concurso_alvo_e_data_prevista(monkeypatch, dados_dir):
    monkeypatch.setattr(ElevenNumbersStrategy, "predict", lambda self, draws, approach="all": _fake_prediction(draws[-1].concurso + 1))

    resultado = gerar_predicao_proximo_concurso(dados_dir=dados_dir)

    assert resultado.concurso_alvo == 103
    # 28/06/2024 é sexta-feira -> próximo dia útil é sábado 29/06/2024
    assert resultado.data_prevista == "29/06/2024"


def test_data_prevista_pula_domingo(monkeypatch, tmp_path):
    # Sábado 29/06/2024 -> próximo sorteio segunda 01/07/2024 (pula domingo)
    _escrever_concurso(tmp_path, 200, "29/06/2024", list(range(1, 16)))
    monkeypatch.setattr(ElevenNumbersStrategy, "predict", lambda self, draws, approach="all": _fake_prediction(draws[-1].concurso + 1))

    resultado = gerar_predicao_proximo_concurso(dados_dir=tmp_path)

    assert resultado.data_prevista == "01/07/2024"


def test_seleciona_top_n_dezenas_por_probabilidade(monkeypatch, dados_dir):
    monkeypatch.setattr(ElevenNumbersStrategy, "predict", lambda self, draws, approach="all": _fake_prediction(draws[-1].concurso + 1))

    resultado = gerar_predicao_proximo_concurso(dados_dir=dados_dir, n_dezenas=15)

    assert resultado.dezenas == list(range(1, 16))
    assert resultado.dezenas == sorted(resultado.dezenas)
    assert len(resultado.confianca_por_dezena) == 15


def test_baseline_e_metadados(monkeypatch, dados_dir):
    monkeypatch.setattr(ElevenNumbersStrategy, "predict", lambda self, draws, approach="all": _fake_prediction(draws[-1].concurso + 1, abordagem="ensemble"))

    resultado = gerar_predicao_proximo_concurso(dados_dir=dados_dir)

    assert resultado.baseline_esperado == BASELINE_ACERTOS_ESPERADO
    assert resultado.abordagem == "ensemble"
    assert resultado.modelo == "ensemble"
    assert resultado.gerado_em


def test_sem_dados_levanta_erro(tmp_path):
    with pytest.raises(ValueError):
        gerar_predicao_proximo_concurso(dados_dir=tmp_path)


def test_nao_usa_concurso_alvo_como_entrada(monkeypatch, dados_dir):
    """Garante que o último draw passado para a strategy é o concurso 102, não 103."""
    chamados = {}

    def fake_predict(self, draws, approach="all"):
        chamados["ultimo_concurso_visto"] = draws[-1].concurso
        return _fake_prediction(draws[-1].concurso + 1)

    monkeypatch.setattr(ElevenNumbersStrategy, "predict", fake_predict)

    resultado = gerar_predicao_proximo_concurso(dados_dir=dados_dir)

    assert chamados["ultimo_concurso_visto"] == 102
    assert resultado.concurso_alvo == 103
