"""Testes da atualização da base com validação automática de predições."""

from __future__ import annotations

import json

import pytest

from lotofacil.infra.dados.banco import DatabaseManager
from lotofacil.servicos import atualizar_base as mod
from lotofacil.servicos.validar_predicoes import resumo_validacoes


class FetcherFalso:
    """Simula a chegada de concursos novos vindos da API da Caixa."""

    def __init__(self, db: DatabaseManager, novos: list[dict]):
        self._db = db
        self._novos = novos

    def sync_new_draws(self) -> int:
        for n in self._novos:
            self._db.upsert_concurso(n["concurso"], n["data"], n["dezenas"])
        return len(self._novos)

    def fetch_latest(self):
        if not self._novos:
            return self._db.get_latest_concurso()
        ultimo = self._novos[-1]
        self._db.upsert_concurso(ultimo["concurso"], ultimo["data"], ultimo["dezenas"])
        return ultimo


@pytest.fixture
def db(tmp_path):
    return DatabaseManager(db_path=tmp_path / "lotofacil_teste.db")


@pytest.fixture
def dados_dir(tmp_path, monkeypatch):
    """Diretório de dados fake usado pela validação (leitura dos resultados)."""
    d = tmp_path / "dados"
    d.mkdir()
    monkeypatch.setattr("lotofacil.servicos.validar_predicoes.DADOS_DIR", d)
    return d


def _escrever_concurso(dados_dir, concurso, data, dezenas):
    (dados_dir / f"concurso_{concurso}.json").write_text(
        json.dumps({"concurso": concurso, "data": data, "dezenas": dezenas}),
        encoding="utf-8",
    )


def _preparar(monkeypatch, db, novos):
    monkeypatch.setattr(mod, "DatabaseManager", lambda: db)
    monkeypatch.setattr(mod, "LotofacilFetcher", lambda: FetcherFalso(db, novos))


def test_predicoes_pendentes_validadas_apos_atualizacao(monkeypatch, db, dados_dir):
    """Predições pendentes do concurso novo ficam validadas após o update."""
    db.upsert_concurso(101, "27/06/2024", list(range(1, 16)))
    db.save_prediction(102, list(range(1, 16)), [0.5] * 15, 0.5, ["ensemble"])

    novo = {"concurso": 102, "data": "28/06/2024", "dezenas": list(range(3, 18))}
    _escrever_concurso(dados_dir, 102, "28/06/2024", novo["dezenas"])
    _preparar(monkeypatch, db, [novo])

    resultado = mod.atualizar_base(escopo="novos")

    assert resultado.total_novos == 1
    assert resultado.ultimo_concurso == 102
    assert db.get_pending_validations() == []
    assert len(resultado.validacoes) == 1
    assert resultado.validacoes[0].concurso_alvo == 102
    # predição 1-15 vs real 3-17 → interseção 3-15 = 13 acertos
    assert resultado.validacoes[0].acertos == 13

    historico = db.get_prediction_history(limit=10)
    assert historico[0]["concurso_alvo"] == 102
    assert historico[0]["acertos"] == 13


def test_validar_false_pula_a_etapa(monkeypatch, db, dados_dir):
    """Com validar=False (--sem-validar na CLI) a predição continua pendente."""
    db.upsert_concurso(101, "27/06/2024", list(range(1, 16)))
    db.save_prediction(102, list(range(1, 16)), [0.5] * 15, 0.5, ["ensemble"])

    novo = {"concurso": 102, "data": "28/06/2024", "dezenas": list(range(3, 18))}
    _escrever_concurso(dados_dir, 102, "28/06/2024", novo["dezenas"])
    _preparar(monkeypatch, db, [novo])

    resultado = mod.atualizar_base(escopo="novos", validar=False)

    assert resultado.total_novos == 1
    assert resultado.validacoes == []
    assert len(db.get_pending_validations()) == 1


def test_sem_concursos_novos_nao_dispara_validacao(monkeypatch, db, dados_dir):
    """Sem concursos novos a validação automática nem é chamada."""
    db.upsert_concurso(101, "27/06/2024", list(range(1, 16)))
    _preparar(monkeypatch, db, [])

    chamadas = []
    monkeypatch.setattr(
        mod, "executar_pos_atualizacao", lambda db=None: chamadas.append(1) or []
    )

    resultado = mod.atualizar_base(escopo="novos")

    assert resultado.total_novos == 0
    assert chamadas == []


def test_escopo_ultimo_tambem_valida(monkeypatch, db, dados_dir):
    db.save_prediction(102, list(range(1, 16)), [0.5] * 15, 0.5, ["ensemble"])
    novo = {"concurso": 102, "data": "28/06/2024", "dezenas": list(range(1, 16))}
    _escrever_concurso(dados_dir, 102, "28/06/2024", novo["dezenas"])
    _preparar(monkeypatch, db, [novo])

    resultado = mod.atualizar_base(escopo="ultimo")

    assert resultado.total_novos == 1
    assert len(resultado.validacoes) == 1
    assert resultado.validacoes[0].acertos == 15


def test_resumo_validacoes_uma_predicao(monkeypatch, db, dados_dir):
    db.save_prediction(3701, list(range(1, 16)), [0.5] * 15, 0.5, ["ensemble"])
    _escrever_concurso(dados_dir, 3701, "28/06/2024", list(range(3, 18)))

    resultados = mod.validar_todas_pendentes(db=db)

    assert resumo_validacoes(resultados) == (
        "1 predição validada para o concurso 3701: 13 acertos"
    )


def test_resumo_validacoes_varios_concursos(monkeypatch, db, dados_dir):
    db.save_prediction(3700, list(range(1, 16)), [0.5] * 15, 0.5, ["ensemble"])
    db.save_prediction(3701, list(range(11, 26)), [0.5] * 15, 0.5, ["ensemble"])
    _escrever_concurso(dados_dir, 3700, "27/06/2024", list(range(1, 16)))
    _escrever_concurso(dados_dir, 3701, "28/06/2024", list(range(1, 16)))

    resultados = mod.validar_todas_pendentes(db=db)

    assert resumo_validacoes(resultados) == (
        "2 predições validadas para os concursos 3700, 3701: 15 e 5 acertos"
    )


def test_resumo_validacoes_vazio():
    assert "Nenhuma predição" in resumo_validacoes([])
