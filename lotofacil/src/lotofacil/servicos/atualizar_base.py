from dataclasses import dataclass
from typing import Literal

from lotofacil.dominio.entidades import Sorteio
from lotofacil.infra.dados.api_caixa import LotofacilFetcher
from lotofacil.infra.dados.banco import DatabaseManager


@dataclass(frozen=True)
class ResultadoAtualizacao:
    total_novos: int
    ultimo_concurso: int
    sorteios_adicionados: list[Sorteio]


def _dict_para_sorteio(d: dict) -> Sorteio:
    return Sorteio(concurso=d["concurso"], data=d["data"], dezenas=d["dezenas"])


def atualizar_base(escopo: Literal["todos", "novos", "ultimo"] = "novos") -> ResultadoAtualizacao:
    fetcher = LotofacilFetcher()
    db = DatabaseManager()

    if escopo == "ultimo":
        result = fetcher.fetch_latest()
        if result is None:
            ultimo = db.get_latest_concurso()
            return ResultadoAtualizacao(
                total_novos=0,
                ultimo_concurso=ultimo["concurso"] if ultimo else 0,
                sorteios_adicionados=[],
            )
        sorteio = _dict_para_sorteio(result)
        return ResultadoAtualizacao(
            total_novos=1,
            ultimo_concurso=sorteio.concurso,
            sorteios_adicionados=[sorteio],
        )

    if escopo == "novos":
        latest_before = db.get_latest_concurso()
        fetcher.sync_new_draws()
        all_concursos = db.get_all_concursos()
        if latest_before:
            novos = [c for c in all_concursos if c["concurso"] > latest_before["concurso"]]
        else:
            novos = all_concursos
        ultimo = db.get_latest_concurso()
        return ResultadoAtualizacao(
            total_novos=len(novos),
            ultimo_concurso=ultimo["concurso"] if ultimo else 0,
            sorteios_adicionados=[_dict_para_sorteio(c) for c in novos],
        )

    latest = fetcher.fetch_latest()
    if latest is None:
        return ResultadoAtualizacao(
            total_novos=0,
            ultimo_concurso=0,
            sorteios_adicionados=[],
        )
    api_max = latest["concurso"]
    novos: list[Sorteio] = []
    for num in range(1, api_max + 1):
        rec = fetcher.fetch_by_concurso(num)
        if rec:
            novos.append(_dict_para_sorteio(rec))
    ultimo = db.get_latest_concurso()
    return ResultadoAtualizacao(
        total_novos=len(novos),
        ultimo_concurso=ultimo["concurso"] if ultimo else 0,
        sorteios_adicionados=novos,
    )
