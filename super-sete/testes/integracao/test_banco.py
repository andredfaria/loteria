from pathlib import Path
from tempfile import TemporaryDirectory

from supersete.infra.dados.banco import DatabaseManager


def test_init_cria_tabela():
    with TemporaryDirectory() as tmp:
        db = DatabaseManager(Path(tmp) / "test.db")
        assert db.count_concursos() == 0


def test_upsert_e_count():
    with TemporaryDirectory() as tmp:
        db = DatabaseManager(Path(tmp) / "test.db")
        db.upsert_concurso(1, "01/01/2020", [0, 1, 2, 3, 4, 5, 6])
        assert db.count_concursos() == 1


def test_upsert_atualiza_existente():
    with TemporaryDirectory() as tmp:
        db = DatabaseManager(Path(tmp) / "test.db")
        db.upsert_concurso(1, "01/01/2020", [0, 1, 2, 3, 4, 5, 6])
        db.upsert_concurso(1, "02/01/2020", [9, 8, 7, 6, 5, 4, 3])
        assert db.count_concursos() == 1
        concursos = db.get_all_concursos()
        assert concursos[0]["digitos"] == [9, 8, 7, 6, 5, 4, 3]


def test_get_all_concursos_ordenado():
    with TemporaryDirectory() as tmp:
        db = DatabaseManager(Path(tmp) / "test.db")
        db.upsert_concurso(2, "01/01/2020", [0, 1, 2, 3, 4, 5, 6])
        db.upsert_concurso(1, "01/01/2019", [9, 8, 7, 6, 5, 4, 3])
        concursos = db.get_all_concursos()
        assert [c["concurso"] for c in concursos] == [1, 2]


def test_get_latest_concurso():
    with TemporaryDirectory() as tmp:
        db = DatabaseManager(Path(tmp) / "test.db")
        assert db.get_latest_concurso() is None
        db.upsert_concurso(1, "01/01/2020", [0, 1, 2, 3, 4, 5, 6])
        db.upsert_concurso(5, "05/01/2020", [9, 8, 7, 6, 5, 4, 3])
        latest = db.get_latest_concurso()
        assert latest["concurso"] == 5
        assert latest["digitos"] == [9, 8, 7, 6, 5, 4, 3]
