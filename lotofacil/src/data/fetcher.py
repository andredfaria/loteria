"""Data fetcher: loads from local JSON files and syncs with API."""

import json
import logging
from pathlib import Path
from typing import Optional

import requests
from tenacity import retry, stop_after_attempt, wait_exponential, before_sleep_log

from core.config import (
    API_LOTOFACIL,
    API_TIMEOUT,
    API_RETRIES,
    API_RETRY_MIN,
    API_RETRY_MAX,
    DATA_RAW,
    NUMBERS_PER_DRAW,
    TOTAL_NUMBERS,
    USER_AGENT,
)
from data.database import DatabaseManager

logger = logging.getLogger(__name__)


def _parse_record(raw: dict) -> Optional[dict]:
    """Validate and normalize a raw draw dict. Returns None if invalid."""
    try:
        concurso = int(raw["concurso"])
        data = str(raw.get("data", ""))
        dezenas = [int(d) for d in raw["dezenas"]]
        if len(dezenas) != NUMBERS_PER_DRAW:
            logger.warning("Concurso %d: expected 15 dezenas, got %d", concurso, len(dezenas))
            return None
        if not all(1 <= d <= TOTAL_NUMBERS for d in dezenas):
            logger.warning("Concurso %d: dezenas out of range 1-25", concurso)
            return None
        return {"concurso": concurso, "data": data, "dezenas": dezenas, "raw": raw}
    except (KeyError, ValueError, TypeError) as exc:
        logger.debug("Skipping invalid record: %s", exc)
        return None


class LotofacilFetcher:
    """Fetches draws from API and persists to DB and raw JSON files."""

    def __init__(self, db: Optional[DatabaseManager] = None, data_dir: Path = DATA_RAW):
        self.db = db or DatabaseManager()
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": USER_AGENT})

    # ── Local file loading ─────────────────────────────────────────────────────

    def _save_raw_json(self, concurso: int, raw: dict):
        path = self.data_dir / f"concurso_{concurso}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(raw, f, indent=2, ensure_ascii=False)

    # ── API ────────────────────────────────────────────────────────────────────

    @retry(
        stop=stop_after_attempt(API_RETRIES),
        wait=wait_exponential(multiplier=1, min=API_RETRY_MIN, max=API_RETRY_MAX),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    def _get_api(self, url: str) -> dict:
        resp = self._session.get(url, timeout=API_TIMEOUT)
        resp.raise_for_status()
        return resp.json()

    def _fetch_concurso_api(self, numero: int) -> Optional[dict]:
        try:
            raw = self._get_api(f"{API_LOTOFACIL}/{numero}")
            return _parse_record(raw)
        except Exception as exc:
            logger.warning("API fetch failed for concurso %d: %s", numero, exc)
            return None

    def _fetch_latest_api(self) -> Optional[dict]:
        try:
            raw = self._get_api(f"{API_LOTOFACIL}/latest")
            return _parse_record(raw)
        except Exception as exc:
            logger.warning("API fetch_latest failed: %s", exc)
            return None

    # ── Public interface ───────────────────────────────────────────────────────

    def fetch_and_save(self, numero: int) -> Optional[dict]:
        """Fetch a single draw from API, save to DB and raw JSON."""
        rec = self._fetch_concurso_api(numero)
        if rec is None:
            return None
        self.db.upsert_concurso(rec["concurso"], rec["data"], rec["dezenas"], rec["raw"])
        self._save_raw_json(rec["concurso"], rec["raw"])
        return {"concurso": rec["concurso"], "data": rec["data"], "dezenas": rec["dezenas"]}

    def fetch_latest(self) -> Optional[dict]:
        """Fetch the most recent draw from API and persist if it's new."""
        rec = self._fetch_latest_api()
        if rec is None:
            return self.db.get_latest_concurso()
        self.db.upsert_concurso(rec["concurso"], rec["data"], rec["dezenas"], rec["raw"])
        self._save_raw_json(rec["concurso"], rec["raw"])
        return {"concurso": rec["concurso"], "data": rec["data"], "dezenas": rec["dezenas"]}

    def sync_new_draws(self) -> int:
        """Sync any draws newer than what's in the DB. Returns count of new draws."""
        latest_local = self.db.get_latest_concurso()
        latest_api = self._fetch_latest_api()
        if latest_api is None or latest_local is None:
            return 0
        start = latest_local["concurso"] + 1
        end = latest_api["concurso"]
        new_count = 0
        for num in range(start, end + 1):
            rec = self._fetch_concurso_api(num)
            if rec:
                self.db.upsert_concurso(rec["concurso"], rec["data"], rec["dezenas"], rec["raw"])
                self._save_raw_json(rec["concurso"], rec["raw"])
                new_count += 1
        logger.info("Synced %d new draws (up to concurso %d)", new_count, end)
        return new_count

    def fetch_range(self, start: int, end: int) -> int:
        """Fetch draws in range [start, end]. Returns count of successful fetches."""
        count = 0
        for num in range(start, end + 1):
            rec = self.fetch_and_save(num)
            if rec:
                count += 1
        logger.info("Fetched %d draws in range [%d, %d]", count, start, end)
        return count
