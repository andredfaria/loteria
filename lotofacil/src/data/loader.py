"""Load Lotofácil draw history from JSON files or SQLite."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from core.config import DATA_RAW
from core.models import Draw
from data.database import DatabaseManager

logger = logging.getLogger(__name__)


def load_draws_from_json(dados_dir: Path = DATA_RAW) -> list[Draw]:
    """
    Load all concurso_N.json files from dados_dir.
    Returns draws sorted by concurso number.
    Silently skips files with JSON errors or invalid data.
    """
    dados_path = Path(dados_dir)
    draws = []

    for arquivo in sorted(dados_path.glob("concurso_*.json")):
        try:
            raw = json.loads(arquivo.read_text(encoding="utf-8"))
            dezenas = sorted(int(d) for d in raw["dezenas"])
            if len(dezenas) != 15:
                logger.warning("Skipping %s: expected 15 dezenas, got %d", arquivo.name, len(dezenas))
                continue
            if len(set(dezenas)) != 15:
                logger.warning("Skipping %s: duplicate dezenas", arquivo.name)
                continue
            if not all(1 <= d <= 25 for d in dezenas):
                logger.warning("Skipping %s: dezenas out of range 1-25", arquivo.name)
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
    logger.info("Loaded %d draws from JSON files", len(draws))
    return draws


def load_draws_from_db(db: DatabaseManager | None = None) -> list[Draw]:
    """Load all draws from SQLite database."""
    mgr = db or DatabaseManager()
    records = mgr.get_all_concursos()
    draws = [Draw(concurso=r["concurso"], data=r["data"], dezenas=r["dezenas"]) for r in records]
    logger.info("Loaded %d draws from database", len(draws))
    return draws


def load_draws(source: str = "db", db: DatabaseManager | None = None,
               json_dir: Path | None = None) -> list[Draw]:
    """
    Load draws from the specified source.

    Args:
        source: "db" for SQLite, "json" for raw JSON files
        db: optional DatabaseManager instance
        json_dir: optional path to JSON directory
    """
    if source == "db":
        return load_draws_from_db(db)
    elif source == "json":
        return load_draws_from_json(json_dir or DATA_RAW)
    else:
        raise ValueError(f"Unknown source: {source}")
