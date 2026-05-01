#!/usr/bin/env python3
"""Process raw draws: migrate JSONs to DB, create processed all_draws.json."""

import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from core.config import DATA_RAW, DATA_PROCESSED
from data.database import DatabaseManager
from data.loader import load_draws_from_json

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def migrate_jsons_to_db(json_dir: Path = DATA_RAW) -> int:
    """Load JSON files and upsert all into the database."""
    db = DatabaseManager()
    draws = load_draws_from_json(json_dir)
    for draw in draws:
        db.upsert_concurso(draw.concurso, draw.data, draw.dezenas)
    logger.info("Migrated %d draws to database", len(draws))
    return len(draws)


def create_all_draws_json(db: DatabaseManager | None = None) -> int:
    """Create a single consolidated JSON file with all draws."""
    mgr = db or DatabaseManager()
    records = mgr.get_all_concursos()
    output = DATA_PROCESSED / "all_draws.json"
    with open(output, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
    logger.info("Created %s with %d draws", output, len(records))
    return len(records)


def main():
    parser = argparse.ArgumentParser(description="Process Lotofácil raw draws")
    parser.add_argument("--migrate", action="store_true",
                        help="Migrate JSON files to database")
    parser.add_argument("--consolidate", action="store_true",
                        help="Create all_draws.json from database")
    parser.add_argument("--all", action="store_true",
                        help="Run migrate and consolidate")
    args = parser.parse_args()

    do_migrate = args.migrate or args.all
    do_consolidate = args.consolidate or args.all

    if not do_migrate and not do_consolidate:
        parser.print_help()
        return

    db = DatabaseManager()

    if do_migrate:
        migrate_jsons_to_db()

    if do_consolidate:
        create_all_draws_json(db)


if __name__ == "__main__":
    main()
