"""Load draw history from dados/concurso_*.json into Draw objects."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import List

from lotofacil.experimentos.config import DATA_DIR, SRC_DIR  # noqa: F401 — sets sys.path

logger = logging.getLogger(__name__)

# Import Draw after sys.path is set by config import
from lotofacil.dominio.entidades import Draw  # noqa: E402


def load_draws(data_dir: Path | None = None, min_concurso: int = 1) -> List[Draw]:
    """Load all concurso_*.json files and return sorted list of Draw objects.

    Args:
        data_dir: Directory to search. Defaults to dados/.
        min_concurso: Skip draws below this number (warmup guard).

    Returns:
        List of Draw objects sorted by concurso ascending.
    """
    root = data_dir or DATA_DIR
    draws: List[Draw] = []

    for fpath in root.glob("concurso_*.json"):
        try:
            raw = json.loads(fpath.read_text(encoding="utf-8"))
            dezenas = raw.get("dezenas", [])
            if not dezenas:
                continue

            draw = Draw(
                concurso=int(raw["concurso"]),
                data=raw["data"],
                dezenas=[int(d) for d in dezenas],
            )
            if draw.concurso >= min_concurso:
                draws.append(draw)
        except (KeyError, ValueError, json.JSONDecodeError) as exc:
            logger.warning("Skipping %s: %s", fpath.name, exc)

    draws.sort(key=lambda d: d.concurso)
    logger.info("Loaded %d draws (concurso %d–%d)", len(draws),
                draws[0].concurso if draws else 0,
                draws[-1].concurso if draws else 0)
    return draws


def load_draws_range(start: int, end: int) -> List[Draw]:
    """Load draws for concurso numbers in [start, end]."""
    all_draws = load_draws()
    return [d for d in all_draws if start <= d.concurso <= end]


def load_draws_last_n(n: int) -> List[Draw]:
    """Load the n most recent draws."""
    all_draws = load_draws()
    return all_draws[-n:] if len(all_draws) > n else all_draws
