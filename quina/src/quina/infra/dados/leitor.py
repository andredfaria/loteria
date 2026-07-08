"""Load Quina draw history from local JSON files."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Union

from quina.dominio.regras import NUMEROS_POR_SORTEIO, TOTAL_NUMEROS

logger = logging.getLogger(__name__)


@dataclass
class Draw:
    concurso: int
    data: str
    dezenas: List[int]  # sorted ints, range 1-80


def load_draws(dados_dir: Union[str, Path]) -> List[Draw]:
    """
    Load all concurso_N.json files from dados_dir.

    Returns draws sorted by concurso number.
    Silently skips files with JSON errors or invalid data.
    """
    dados_path = Path(dados_dir)
    draws: List[Draw] = []

    for arquivo in dados_path.glob("concurso_*.json"):
        try:
            raw = json.loads(arquivo.read_text(encoding="utf-8"))
            dezenas = sorted(int(d) for d in raw["dezenas"])
            if len(dezenas) != NUMEROS_POR_SORTEIO:
                logger.warning(
                    "Skipping %s: expected %d dezenas, got %d",
                    arquivo.name, NUMEROS_POR_SORTEIO, len(dezenas),
                )
                continue
            if len(set(dezenas)) != NUMEROS_POR_SORTEIO:
                logger.warning("Skipping %s: dezenas contains duplicates", arquivo.name)
                continue
            if not all(1 <= d <= TOTAL_NUMEROS for d in dezenas):
                logger.warning(
                    "Skipping %s: dezenas out of range 1-%d", arquivo.name, TOTAL_NUMEROS
                )
                continue
            draws.append(Draw(
                concurso=int(raw["concurso"]),
                data=raw.get("data", ""),
                dezenas=dezenas,
            ))
        except Exception as exc:
            logger.warning("Skipping %s: %s", arquivo.name, exc)
            continue

    draws.sort(key=lambda d: d.concurso)
    return draws
