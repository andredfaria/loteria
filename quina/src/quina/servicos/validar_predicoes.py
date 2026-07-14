from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from quina.infra.dados.leitor import load_draws
from quina.dominio.regras import contar_acertos


@dataclass(frozen=True)
class ResultadoValidacao:
    concurso: int
    dezenas_sugeridas: list[int]
    dezenas_reais: list[int]
    acertos: int


def validar_predicao(
    concurso: int,
    dezenas_sugeridas: list[int],
    dados_dir: Optional[Path] = None,
) -> ResultadoValidacao:
    from pathlib import Path as _Path
    dados_dir = dados_dir or _Path(__file__).resolve().parent.parent.parent.parent / "dados"
    draws = load_draws(dados_dir)
    alvo = [d for d in draws if d.concurso == concurso]
    if not alvo:
        raise ValueError(f"Concurso {concurso} não encontrado")
    reais = alvo[0].dezenas
    acertos = contar_acertos(dezenas_sugeridas, reais)
    return ResultadoValidacao(
        concurso=concurso,
        dezenas_sugeridas=sorted(dezenas_sugeridas),
        dezenas_reais=sorted(reais),
        acertos=acertos,
    )