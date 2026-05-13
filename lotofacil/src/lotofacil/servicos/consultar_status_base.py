from dataclasses import dataclass

from lotofacil.infra.dados.banco import DatabaseManager


@dataclass(frozen=True)
class StatusBase:
    total_concursos: int
    ultimo_concurso: int
    primeiro_concurso: int
    data_ultima_atualizacao: str


def consultar_status_base() -> StatusBase:
    db = DatabaseManager()
    total = db.count_concursos()
    if total == 0:
        return StatusBase(
            total_concursos=0,
            ultimo_concurso=0,
            primeiro_concurso=0,
            data_ultima_atualizacao="",
        )
    todos = db.get_all_concursos()
    primeiro = todos[0]
    ultimo = todos[-1]
    return StatusBase(
        total_concursos=total,
        ultimo_concurso=ultimo["concurso"],
        primeiro_concurso=primeiro["concurso"],
        data_ultima_atualizacao=ultimo["data"],
    )
