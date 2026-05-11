"""Backfill historical climate data via Open-Meteo Archive API.

The forecast API (used by src/coleta/busca_clima.py) only has recent data.
The archive endpoint covers 1940→today, enabling climate features for the
full draw history.

Saves files in the same format as busca_clima.py so existing loaders work.
Run: python -m lotofacil_lab.coleta.backfill_clima_archive --ultimos 500
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from lotofacil_lab.config import (
    ARCHIVE_API_URL, ARCHIVE_BATCH_DAYS, ARCHIVE_DELAY_SECONDS,
    LATITUDE, LONGITUDE, TIMEZONE, DATA_DIR, CLIMATE_DIR, SRC_DIR,
)

logger = logging.getLogger(__name__)

# Hourly fields to request — superset of the forecast fields + humidity/wind/pressure
_HOURLY_FIELDS = ",".join([
    "temperature_2m",
    "precipitation",
    "precipitation_probability",
    "weathercode",
    "relativehumidity_2m",
    "surface_pressure",
    "windspeed_10m",
])

_FILENAME_RE = re.compile(r"clima_concurso(\d+)-\d{4}-\d{2}-\d{2}\.json")
_HORA_SORTEIO = 21


def _already_fetched(concurso: int) -> bool:
    """True if any clima_concurso<N>-*.json exists for this concurso."""
    return bool(list(CLIMATE_DIR.glob(f"clima_concurso{concurso}-*.json")))


def _load_existing_concursos() -> set:
    """Return set of concurso numbers already fetched."""
    existing: set = set()
    if not CLIMATE_DIR.exists():
        return existing
    for fpath in CLIMATE_DIR.glob("clima_concurso*.json"):
        m = _FILENAME_RE.match(fpath.name)
        if m:
            existing.add(int(m.group(1)))
    return existing


def _processar_resumo_extended(hourly: Dict) -> Dict:
    """Extended version of _processar_resumo with extra fields."""
    temps = [t for t in hourly.get("temperature_2m", []) if t is not None]
    precip = [p for p in (hourly.get("precipitation") or hourly.get("precipitation_probability", [])) if p is not None]
    precip_prob = [p for p in hourly.get("precipitation_probability", []) if p is not None]
    codes = [c for c in hourly.get("weathercode", []) if c is not None]
    humidity = [h for h in hourly.get("relativehumidity_2m", []) if h is not None]
    pressure = [p for p in hourly.get("surface_pressure", []) if p is not None]
    wind = [w for w in hourly.get("windspeed_10m", []) if w is not None]

    def _at(lst, idx):
        return lst[idx] if len(lst) > idx and lst[idx] is not None else None

    code_counts: Dict[int, int] = {}
    for c in codes:
        if c is not None:
            code_counts[c] = code_counts.get(c, 0) + 1
    code_dominante = max(code_counts, key=code_counts.get) if code_counts else None

    CODIGO_CLIMA = {
        0: "Céu limpo", 1: "Principalmente limpo", 2: "Parcialmente nublado",
        3: "Nublado", 45: "Neblina", 51: "Garoa leve", 61: "Chuva leve",
        63: "Chuva moderada", 65: "Chuva forte", 80: "Pancadas leves",
        81: "Pancadas moderadas", 82: "Pancadas fortes", 95: "Trovoada",
    }

    resumo = {
        "temp_min": round(min(temps), 1) if temps else None,
        "temp_max": round(max(temps), 1) if temps else None,
        "temp_media": round(sum(temps) / len(temps), 1) if temps else None,
        "temp_sorteio": _at(hourly.get("temperature_2m", []), _HORA_SORTEIO),
        "precipitacao_media": round(sum(precip_prob) / len(precip_prob), 1) if precip_prob else None,
        "precipitacao_sorteio": _at(hourly.get("precipitation_probability", []), _HORA_SORTEIO),
        "weathercode_sorteio": _at(hourly.get("weathercode", []), _HORA_SORTEIO),
        "weathercode_dominante": code_dominante,
        "condicao_sorteio": CODIGO_CLIMA.get(_at(hourly.get("weathercode", []), _HORA_SORTEIO), "Desconhecida"),
        "condicao_dominante": CODIGO_CLIMA.get(code_dominante, "Desconhecida"),
        # Extended fields
        "umidade_sorteio": _at(hourly.get("relativehumidity_2m", []), _HORA_SORTEIO),
        "pressao_sorteio": _at(hourly.get("surface_pressure", []), _HORA_SORTEIO),
        "vento_sorteio": _at(hourly.get("windspeed_10m", []), _HORA_SORTEIO),
    }
    return resumo


@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=2, max=30))
def _fetch_archive_batch(start_date: str, end_date: str) -> Optional[Dict]:
    """Fetch one batch from Open-Meteo Archive API."""
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": _HOURLY_FIELDS,
        "timezone": TIMEZONE,
    }
    resp = requests.get(ARCHIVE_API_URL, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _split_hourly_by_day(hourly: Dict) -> Dict[str, Dict]:
    """Split hourly arrays (length 24*N_days) into per-day dicts."""
    times = hourly.get("time", [])
    if not times:
        return {}

    day_data: Dict[str, Dict] = {}
    keys = [k for k in hourly if k != "time"]

    for idx, ts in enumerate(times):
        day = ts[:10]  # "YYYY-MM-DD"
        if day not in day_data:
            day_data[day] = {k: [] for k in keys}
        for k in keys:
            val = hourly.get(k, [])
            day_data[day][k].append(val[idx] if idx < len(val) else None)

    return day_data


def _save_climate(concurso: int, date_iso: str, resumo: Dict, hourly: Dict) -> None:
    CLIMATE_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "concurso": concurso,
        "data": date_iso,
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "timezone": TIMEZONE,
        "hourly_units": {"time": "iso8601", "temperature_2m": "°C",
                          "precipitation": "mm", "weathercode": "wmo code"},
        "hourly": hourly,
        "resumo": resumo,
    }
    fname = CLIMATE_DIR / f"clima_concurso{concurso}-{date_iso}.json"
    fname.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.debug("Saved %s", fname.name)


def _load_draw_dates() -> List[Tuple[int, str]]:
    """Return [(concurso, YYYY-MM-DD), ...] sorted by concurso."""
    from lotofacil_lab.data.draws_loader import load_draws
    draws = load_draws()
    result = []
    for d in draws:
        try:
            if "/" in d.data:
                iso = datetime.strptime(d.data.strip(), "%d/%m/%Y").strftime("%Y-%m-%d")
            else:
                iso = d.data.strip()
            result.append((d.concurso, iso))
        except ValueError:
            pass
    return sorted(result)


def backfill(
    concurso_from: int = 1,
    concurso_to: int | None = None,
    ultimos: int | None = None,
    force: bool = False,
) -> int:
    """Download climate data for draws that are missing it.

    Returns number of draws successfully fetched.
    """
    all_dates = _load_draw_dates()
    if not all_dates:
        logger.error("No draw dates found. Run busca_sorteios.py first.")
        return 0

    # Filter target range
    if ultimos:
        all_dates = all_dates[-ultimos:]
    else:
        max_conc = concurso_to or all_dates[-1][0]
        all_dates = [(c, d) for c, d in all_dates if concurso_from <= c <= max_conc]

    existing = _load_existing_concursos() if not force else set()
    targets = [(c, d) for c, d in all_dates if c not in existing]

    if not targets:
        logger.info("All %d draws already have climate data.", len(all_dates))
        return 0

    logger.info("Backfilling %d/%d draws (force=%s)...", len(targets), len(all_dates), force)

    # Group into date batches of ARCHIVE_BATCH_DAYS
    i = 0
    fetched = 0

    while i < len(targets):
        batch = targets[i:i + ARCHIVE_BATCH_DAYS]
        start_date = batch[0][1]
        end_date = batch[-1][1]

        logger.info("Fetching %s → %s (%d draws)...", start_date, end_date, len(batch))

        try:
            response = _fetch_archive_batch(start_date, end_date)
        except Exception as exc:
            logger.error("API error for batch %s–%s: %s", start_date, end_date, exc)
            i += len(batch)
            time.sleep(ARCHIVE_DELAY_SECONDS)
            continue

        hourly = response.get("hourly", {})
        daily_data = _split_hourly_by_day(hourly)

        for concurso, iso_date in batch:
            day_hourly = daily_data.get(iso_date)
            if not day_hourly:
                logger.warning("No archive data for %s (concurso %d)", iso_date, concurso)
                continue
            resumo = _processar_resumo_extended(day_hourly)
            if resumo:
                _save_climate(concurso, iso_date, resumo, day_hourly)
                fetched += 1

        i += len(batch)
        time.sleep(ARCHIVE_DELAY_SECONDS)

    logger.info("Backfill complete: %d draws fetched.", fetched)
    return fetched


def main() -> None:
    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        level=logging.INFO,
    )
    parser = argparse.ArgumentParser(description="Backfill historical climate data.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--ultimos", type=int, metavar="N",
                       help="Fetch the N most recent draws")
    group.add_argument("--from", dest="from_c", type=int, default=1, metavar="CONCURSO",
                       help="First concurso (default: 1)")
    parser.add_argument("--to", dest="to_c", type=int, default=None, metavar="CONCURSO",
                        help="Last concurso (default: latest)")
    parser.add_argument("--force", action="store_true",
                        help="Re-fetch even if file already exists")
    args = parser.parse_args()

    count = backfill(
        concurso_from=args.from_c,
        concurso_to=args.to_c,
        ultimos=args.ultimos,
        force=args.force,
    )
    print(f"Done: {count} draws fetched.")


if __name__ == "__main__":
    main()
