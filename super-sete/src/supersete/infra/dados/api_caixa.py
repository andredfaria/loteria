import json
import logging
from pathlib import Path
from typing import List, Optional

import requests
from tenacity import before_sleep_log, retry, stop_after_attempt, wait_exponential

from supersete.infra.config import (
    API_SUPERSETE,
    API_RETRIES,
    API_RETRY_MAX,
    API_RETRY_MIN,
    API_TIMEOUT,
    DADOS_DIR,
    DIGITOS,
    NUM_COLUNAS,
    USER_AGENT,
)
from supersete.infra.dados.banco import DatabaseManager

logger = logging.getLogger(__name__)


def _parse_record(raw: dict) -> Optional[dict]:
    try:
        concurso = int(raw["concurso"])
        data = str(raw.get("data", ""))
        digitos = [int(d) for d in raw["dezenas"]]
        if len(digitos) != NUM_COLUNAS:
            logger.warning("Concurso %d: expected %d digitos, got %d", concurso, NUM_COLUNAS, len(digitos))
            return None
        if not all(d in DIGITOS for d in digitos):
            logger.warning("Concurso %d: digitos out of range 0-9", concurso)
            return None
        return {"concurso": concurso, "data": data, "digitos": digitos, "raw": raw}
    except (KeyError, ValueError, TypeError) as exc:
        logger.debug("Skipping invalid record: %s", exc)
        return None


class SuperseteFetcher:
    def __init__(self, db: Optional[DatabaseManager] = None, data_dir: Path = DADOS_DIR):
        self.db = db or DatabaseManager()
        self.data_dir = data_dir
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": USER_AGENT})

    # -- Local file loading -------------------------------------------------

    def _load_local_files(self) -> List[dict]:
        records = []
        files = sorted(self.data_dir.glob("concurso_*.json"))
        logger.info("Loading %d local JSON files from %s", len(files), self.data_dir)
        for f in files:
            try:
                with open(f, encoding="utf-8") as fh:
                    raw = json.load(fh)
                rec = _parse_record(raw)
                if rec:
                    records.append(rec)
            except Exception as exc:
                logger.debug("Skipping %s: %s", f.name, exc)
        logger.info("Loaded %d valid concursos from local files", len(records))
        return records

    # -- API ------------------------------------------------------------------

    @retry(
        stop=stop_after_attempt(API_RETRIES),
        wait=wait_exponential(multiplier=1, min=API_RETRY_MIN, max=API_RETRY_MAX),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    def _get_api(self, url: str) -> dict | list:
        resp = self._session.get(url, timeout=API_TIMEOUT)
        resp.raise_for_status()
        return resp.json()

    def _fetch_concurso_api(self, numero: int) -> Optional[dict]:
        try:
            raw = self._get_api(f"{API_SUPERSETE}/{numero}")
            return _parse_record(raw)
        except Exception as exc:
            logger.warning("API fetch failed for concurso %d: %s", numero, exc)
            return None

    def _fetch_latest_api(self) -> Optional[dict]:
        try:
            raw = self._get_api(f"{API_SUPERSETE}/latest")
            return _parse_record(raw)
        except Exception as exc:
            logger.warning("API fetch_latest failed: %s", exc)
            return None

    def _fetch_all_api(self) -> List[dict]:
        try:
            raw_list = self._get_api(API_SUPERSETE)
            records = []
            for raw in raw_list:
                rec = _parse_record(raw)
                if rec:
                    records.append(rec)
            logger.info("Fetched %d concursos from bulk API", len(records))
            return records
        except Exception as exc:
            logger.warning("API bulk fetch failed: %s", exc)
            return []

    def _save_concurso_json(self, concurso: int, raw: dict) -> None:
        path = self.data_dir / f"concurso_{concurso}.json"
        if not path.exists():
            path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")

    # -- Public interface -----------------------------------------------------

    def fetch_all_results(self) -> List[dict]:
        records = self._load_local_files()
        for rec in records:
            self.db.upsert_concurso(rec["concurso"], rec["data"], rec["digitos"], rec["raw"])
        return self.db.get_all_concursos()

    def fetch_latest(self) -> Optional[dict]:
        rec = self._fetch_latest_api()
        if rec is None:
            return self.db.get_latest_concurso()
        self.db.upsert_concurso(rec["concurso"], rec["data"], rec["digitos"], rec["raw"])
        self._save_concurso_json(rec["concurso"], rec["raw"])
        return {"concurso": rec["concurso"], "data": rec["data"], "digitos": rec["digitos"]}

    def fetch_by_concurso(self, numero: int) -> Optional[dict]:
        all_concursos = self.db.get_all_concursos()
        existing = {r["concurso"]: r for r in all_concursos}
        if numero in existing:
            return existing[numero]
        rec = self._fetch_concurso_api(numero)
        if rec:
            self.db.upsert_concurso(rec["concurso"], rec["data"], rec["digitos"], rec["raw"])
            return {"concurso": rec["concurso"], "data": rec["data"], "digitos": rec["digitos"]}
        return None

    def sync_new_draws(self) -> int:
        if self.db.count_concursos() == 0:
            records = self._fetch_all_api()
            if records:
                for rec in records:
                    self.db.upsert_concurso(rec["concurso"], rec["data"], rec["digitos"], rec["raw"])
                    self._save_concurso_json(rec["concurso"], rec["raw"])
                logger.info("Synced %d draws via bulk API", len(records))
                return len(records)

        latest_local = self.db.get_latest_concurso()
        latest_api = self._fetch_latest_api()
        if latest_api is None:
            return 0
        start = (latest_local["concurso"] + 1) if latest_local else 1
        end = latest_api["concurso"]
        new_count = 0
        for num in range(start, end + 1):
            rec = self._fetch_concurso_api(num)
            if rec:
                self.db.upsert_concurso(rec["concurso"], rec["data"], rec["digitos"], rec["raw"])
                self._save_concurso_json(rec["concurso"], rec["raw"])
                new_count += 1
        logger.info("Synced %d new draws (up to concurso %d)", new_count, end)
        return new_count
