from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from lotofacil.dominio.entidades import Portfolio
from lotofacil.infra.config import DADOS_DIR, JOGOS_DIR

TABELA_PREMIOS = {11: 7.00, 12: 14.00, 13: 35.00, 14: 2_000.00, 15: 1_500_000.00}


@dataclass(frozen=True)
class ResultadoValidacaoJogo:
    jogo_idx: int
    tier: str
    dezenas: List[int]
    acertos: int
    premio: float


@dataclass(frozen=True)
class ResultadoValidacaoPortfolio:
    concurso: int
    dezenas_reais: List[int]
    jogos: List[ResultadoValidacaoJogo]
    total_acertos_11: int = 0
    total_acertos_12: int = 0
    total_acertos_13: int = 0
    total_acertos_14: int = 0
    total_acertos_15: int = 0
    custo_total: float = 0.0
    premio_total: float = 0.0

    def __post_init__(self):
        acertos_map = {11: 0, 12: 0, 13: 0, 14: 0, 15: 0}
        custo = 0
        premio = 0
        for jogo in self.jogos:
            custo += 3.50
            if jogo.acertos in TABELA_PREMIOS:
                acertos_map[jogo.acertos] += 1
                premio += TABELA_PREMIOS[jogo.acertos]
        object.__setattr__(self, "total_acertos_11", acertos_map[11])
        object.__setattr__(self, "total_acertos_12", acertos_map[12])
        object.__setattr__(self, "total_acertos_13", acertos_map[13])
        object.__setattr__(self, "total_acertos_14", acertos_map[14])
        object.__setattr__(self, "total_acertos_15", acertos_map[15])
        object.__setattr__(self, "custo_total", custo)
        object.__setattr__(self, "premio_total", premio)

    @property
    def roi_percent(self) -> float:
        if self.custo_total == 0:
            return 0.0
        return (self.premio_total - self.custo_total) / self.custo_total * 100


def validar_portfolio(
    concurso: int, arquivo_portfolio: Optional[Path] = None
) -> ResultadoValidacaoPortfolio:
    result_path = DADOS_DIR / f"concurso_{concurso}.json"
    if not result_path.exists():
        raise FileNotFoundError(f"Sorteio do concurso {concurso} não encontrado em {result_path}")

    raw = json.loads(result_path.read_text(encoding="utf-8"))
    dezenas_reais = sorted(int(d) for d in raw["dezenas"])

    if arquivo_portfolio is None:
        arquivo_portfolio = JOGOS_DIR / f"portfolio_{concurso}.json"

    if not arquivo_portfolio.exists():
        raise FileNotFoundError(f"Portfólio não encontrado em {arquivo_portfolio}")

    portfolio_data = json.loads(arquivo_portfolio.read_text(encoding="utf-8"))

    jogos_validados: List[ResultadoValidacaoJogo] = []
    jogo_idx = 1
    for tier in ("conservador", "equilibrado", "agressivo"):
        for game in portfolio_data.get(tier, []):
            hits = len(set(game) & set(dezenas_reais))
            premio = TABELA_PREMIOS.get(hits, 0.0)
            jogos_validados.append(
                ResultadoValidacaoJogo(
                    jogo_idx=jogo_idx,
                    tier=tier,
                    dezenas=sorted(game),
                    acertos=hits,
                    premio=premio,
                )
            )
            jogo_idx += 1

    return ResultadoValidacaoPortfolio(
        concurso=concurso,
        dezenas_reais=dezenas_reais,
        jogos=jogos_validados,
    )
