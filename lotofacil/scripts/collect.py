#!/usr/bin/env python3
"""Collect Lotofácil draws from API and persist to database and raw JSON files."""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from data.database import DatabaseManager
from data.fetcher import LotofacilFetcher

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Collect Lotofácil draws from API")
    parser.add_argument("--from", type=int, default=None, dest="start",
                        help="Start concurso number")
    parser.add_argument("--to", type=int, default=None, dest="end",
                        help="End concurso number")
    parser.add_argument("--latest", action="store_true",
                        help="Fetch only the latest draw")
    parser.add_argument("--sync", action="store_true",
                        help="Sync draws newer than what's in DB")
    args = parser.parse_args()

    db = DatabaseManager()
    fetcher = LotofacilFetcher(db=db)

    if args.latest:
        logger.info("Fetching latest draw...")
        rec = fetcher.fetch_latest()
        if rec:
            logger.info("Latest: concurso %d (%s) %s", rec["concurso"], rec["data"], rec["dezenas"])
        else:
            logger.error("Failed to fetch latest draw")

    elif args.sync:
        logger.info("Syncing new draws...")
        count = fetcher.sync_new_draws()
        logger.info("Synced %d new draws", count)

    elif args.start and args.end:
        logger.info("Fetching draws %d to %d...", args.start, args.end)
        count = fetcher.fetch_range(args.start, args.end)
        logger.info("Fetched %d draws", count)

    else:
        logger.info("No action specified. Use --latest, --sync, or --from N --to M")


if __name__ == "__main__":
    main()
