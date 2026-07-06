"""Tests for TreinoRegistry job output persistence."""
import pytest
from lotofacil.interface.painel.treino_registry import TreinoRegistry


@pytest.fixture
def reg(tmp_path):
    return TreinoRegistry(tmp_path / "treinos.db")


def test_create_job_and_write_lines(reg):
    reg.create_job("task_001")
    reg.write_line("task_001", "linha 1")
    reg.write_line("task_001", "linha 2")
    result = reg.poll_job("task_001", 0)
    assert result["lines"] == ["linha 1", "linha 2"]
    assert result["done"] is False
    assert "success" not in result


def test_finish_job_success(reg):
    reg.create_job("task_002")
    reg.write_line("task_002", "saída")
    reg.finish_job("task_002", True)
    result = reg.poll_job("task_002", 0)
    assert result["done"] is True
    assert result["success"] is True
    assert result["lines"] == ["saída"]


def test_finish_job_failure(reg):
    reg.create_job("task_003")
    reg.finish_job("task_003", False)
    result = reg.poll_job("task_003", 0)
    assert result["done"] is True
    assert result["success"] is False
    assert result["lines"] == []


def test_poll_offset_pagination(reg):
    reg.create_job("task_004")
    reg.write_line("task_004", "linha A")
    reg.write_line("task_004", "linha B")
    reg.write_line("task_004", "linha C")

    first = reg.poll_job("task_004", 0)
    assert first["lines"] == ["linha A", "linha B", "linha C"]
    assert first["next_offset"] > 0

    second = reg.poll_job("task_004", first["next_offset"])
    assert second["lines"] == []
    assert second["next_offset"] == first["next_offset"]


def test_poll_unknown_task_returns_done_false(reg):
    result = reg.poll_job("nonexistent_task", 0)
    assert result["done"] is True
    assert result["success"] is False
    assert result["lines"] == []


def test_criar_e_buscar_backtest(reg):
    reg.criar_backtest("bt_001", ["base+temp+priors"], 100, 200, 25)
    bt = reg.buscar_backtest("bt_001")
    assert bt["status"] == "running"
    assert bt["configs"] == ["base+temp+priors"]
    assert bt["start_concurso"] == 100
    assert bt["end_concurso"] == 200
    assert bt["retrain_every"] == 25


def test_registrar_resultado_backtest_marca_completed(reg):
    reg.criar_backtest("bt_002", ["base+temp+priors"], 100, 200, 25)
    reg.registrar_resultado_backtest("bt_002", "/tmp/backtest_bt_002.json")
    bt = reg.buscar_backtest("bt_002")
    assert bt["status"] == "completed"
    assert bt["resultado_path"] == "/tmp/backtest_bt_002.json"
    assert bt["concluido_em"] is not None


def test_marcar_falha_backtest(reg):
    reg.criar_backtest("bt_003", ["base+temp+priors"], 100, 200, 25)
    reg.marcar_falha_backtest("bt_003")
    bt = reg.buscar_backtest("bt_003")
    assert bt["status"] == "failed"


def test_listar_backtests_ordenado_por_criacao_desc(reg):
    reg.criar_backtest("bt_004", ["base+temp+priors"], 1, 2, 1)
    reg.criar_backtest("bt_005", ["base+temp+priors+lua"], 1, 2, 1)
    listagem = reg.listar_backtests()
    assert [b["id"] for b in listagem] == ["bt_005", "bt_004"]


def test_deletar_backtest(reg):
    reg.criar_backtest("bt_006", ["base+temp+priors"], 1, 2, 1)
    assert reg.deletar_backtest("bt_006") is True
    assert reg.buscar_backtest("bt_006") is None


def test_buscar_backtest_inexistente_retorna_none(reg):
    assert reg.buscar_backtest("nao_existe") is None
