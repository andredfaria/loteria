"""Climate data loader for the lab pipeline.

Loads climate JSON files from dados/clima/ and provides:
- load_all_climate() → {concurso: resumo_dict}
- normalize_climate(resumo) → list of 8 normalized floats
- get_climate_matrix(draws) → np.ndarray shape (n, 8)
- get_coverage_pct(draws) → float

Draws without climate data get zero vectors (graceful degradation).
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Dict, List

import numpy as np

from lotofacil.experimentos.config import CLIMATE_DIR

logger = logging.getLogger(__name__)

CLIMATE_FEATURE_NAMES = [
    "temp_min",
    "temp_max",
    "temp_media",
    "temp_sorteio",
    "precip_media",
    "precip_sorteio",
    "wcode_sorteio",
    "wcode_dominant",
]
N_CLIMATE_FEATURES = len(CLIMATE_FEATURE_NAMES)

_FILENAME_PATTERN = re.compile(r"clima_concurso(\d+)-\d{4}-\d{2}-\d{2}\.json")

TEMP_NORM = 40.0
PRECIP_NORM = 100.0
WCODE_NORM = 99.0


def load_all_climate() -> Dict[int, Dict]:
    """Load all climate JSON files and return {concurso_number: resumo_dict}."""
    climate_data: Dict[int, Dict] = {}

    if not CLIMATE_DIR.exists():
        logger.info("Climate directory not found: %s", CLIMATE_DIR)
        return climate_data

    for fpath in CLIMATE_DIR.glob("clima_concurso*.json"):
        match = _FILENAME_PATTERN.match(fpath.name)
        if not match:
            continue
        try:
            concurso_num = int(match.group(1))
            with open(fpath, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            resumo = data.get("resumo", {})
            if resumo:
                climate_data[concurso_num] = resumo
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.warning("Skipping climate file %s: %s", fpath.name, e)

    logger.info("Loaded climate data for %d contests", len(climate_data))
    return climate_data


def normalize_climate(resumo: Dict) -> List[float]:
    """Convert a climate resumo dict into a normalized 8-float feature vector."""
    return [
        (resumo.get("temp_min") or 0.0) / TEMP_NORM,
        (resumo.get("temp_max") or 0.0) / TEMP_NORM,
        (resumo.get("temp_media") or 0.0) / TEMP_NORM,
        (resumo.get("temp_sorteio") or 0.0) / TEMP_NORM,
        (resumo.get("precipitacao_media") or 0.0) / PRECIP_NORM,
        (resumo.get("precipitacao_sorteio") or 0.0) / PRECIP_NORM,
        (resumo.get("weathercode_sorteio") or 0) / WCODE_NORM,
        (resumo.get("weathercode_dominante") or 0) / WCODE_NORM,
    ]


def get_climate_matrix(draws) -> np.ndarray:
    """Return climate features aligned with draws, shape (n, 8), float32."""
    climate_map = load_all_climate()
    n = len(draws)
    out = np.zeros((n, N_CLIMATE_FEATURES), dtype=np.float32)
    missing = 0

    for i, draw in enumerate(draws):
        resumo = climate_map.get(draw.concurso)
        if resumo:
            out[i] = normalize_climate(resumo)
        else:
            missing += 1

    if missing:
        coverage = (n - missing) / n * 100
        logger.info("Climate coverage: %.1f%% (%d/%d draws)", coverage, n - missing, n)

    return out


def get_coverage_pct(draws) -> float:
    """Return percentage of draws that have climate data."""
    climate_map = load_all_climate()
    if not draws:
        return 0.0
    covered = sum(1 for d in draws if d.concurso in climate_map)
    return covered / len(draws) * 100


def fetch_climate_from_api(date_iso: str) -> dict | None:
    """Fetch climate data from Open-Meteo Archive API for a single date.

    Returns a resumo dict (same format as saved climate files) or None.
    """
    import logging
    import requests as req_lib
    logger = logging.getLogger(__name__)
    try:
        from lotofacil.experimentos.config import ARCHIVE_API_URL, LATITUDE, LONGITUDE, TIMEZONE
        params = {
            "latitude": LATITUDE,
            "longitude": LONGITUDE,
            "start_date": date_iso,
            "end_date": date_iso,
            "hourly": "temperature_2m,precipitation,precipitation_probability,weathercode",
            "timezone": TIMEZONE,
        }
        resp = req_lib.get(ARCHIVE_API_URL, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        hourly = data.get("hourly", {})
        times = hourly.get("time", [])
        if not times:
            return None

        temps = [t for t in hourly.get("temperature_2m", []) if t is not None]
        precip_prob = [p for p in hourly.get("precipitation_probability", []) if p is not None]
        codes = [c for c in hourly.get("weathercode", []) if c is not None]
        hora_sorteio = 21

        def _at(lst, idx):
            return lst[idx] if len(lst) > idx and lst[idx] is not None else None

        code_counts: dict[int, int] = {}
        for c in codes:
            if c is not None:
                code_counts[c] = code_counts.get(c, 0) + 1
        code_dominante = max(code_counts, key=code_counts.get) if code_counts else None

        resumo = {
            "temp_min": round(min(temps), 1) if temps else None,
            "temp_max": round(max(temps), 1) if temps else None,
            "temp_media": round(sum(temps) / len(temps), 1) if temps else None,
            "temp_sorteio": _at(hourly.get("temperature_2m", []), hora_sorteio),
            "precipitacao_media": round(sum(precip_prob) / len(precip_prob), 1) if precip_prob else None,
            "precipitacao_sorteio": _at(hourly.get("precipitation_probability", []), hora_sorteio),
            "weathercode_sorteio": _at(hourly.get("weathercode", []), hora_sorteio),
            "weathercode_dominante": code_dominante,
        }
        return resumo
    except Exception as exc:
        logger.warning("Climate API fetch failed for %s: %s", date_iso, exc)
        return None
