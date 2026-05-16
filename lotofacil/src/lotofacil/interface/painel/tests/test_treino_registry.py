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
