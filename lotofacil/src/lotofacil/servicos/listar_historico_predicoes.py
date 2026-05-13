from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from lotofacil.infra.dados.banco import DatabaseManager


@dataclass(frozen=True)
class HistoricoPredicaoInfo:
    concurso_alvo: int
    dezenas_sugeridas: List[int]
    confianca_media: float
    acertos: Optional[int]
    criado_em: str
    validado_em: Optional[str]


def listar_historico_predicoes(limite: int = 50) -> List[HistoricoPredicaoInfo]:
    db = DatabaseManager()
    registros = db.get_prediction_history(limit=limite)
    return [
        HistoricoPredicaoInfo(
            concurso_alvo=r["concurso_alvo"],
            dezenas_sugeridas=r["dezenas_sugeridas"],
            confianca_media=r["confianca_media"],
            acertos=r.get("acertos"),
            criado_em=r["criado_em"],
            validado_em=r.get("validado_em"),
        )
        for r in registros
    ]
