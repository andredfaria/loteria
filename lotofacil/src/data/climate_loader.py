"""Climate data loader for Lotofácil draw analysis.

Loads climate JSON files from dados/clima/clima_concurso*.json
and maps them to draw contest numbers for ML feature extraction.
Auto-fetches from Open-Meteo API when local data is missing.
"""

from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

DIRETORIO_BASE = Path(__file__).resolve().parent.parent.parent
DIRETORIO_CLIMA = DIRETORIO_BASE / "dados" / "clima"

API_URL = "https://api.open-meteo.com/v1/forecast"
LATITUDE = -23.55
LONGITUDE = -46.63
TIMEZONE = "America/Sao_Paulo"
DELAY_REQUISICOES = 0.8

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

TEMP_NORM = 40.0
PRECIP_NORM = 100.0
WCODE_NORM = 99.0

_FILENAME_PATTERN = re.compile(r"clima_concurso(\d+)-\d{4}-\d{2}-\d{2}\.json")

_local_cache: Dict[int, Dict] = {}
_last_fetch_time: float = 0.0
_API_START_DATE = "2026-03-01"
_NO_DATA_MARKER = {"_no_data": True}


def load_all_climate() -> Dict[int, Dict]:
    """Load all climate files and return {concurso_number: resumo_dict}.

    Parses filename to extract concurso number.
    Skips malformed files silently.
    """
    climate_data: Dict[int, Dict] = {}

    if not DIRETORIO_CLIMA.exists():
        logger.info("Climate directory not found: %s", DIRETORIO_CLIMA)
        return climate_data

    for fpath in DIRETORIO_CLIMA.glob("clima_concurso*.json"):
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
    """Convert a climate resumo dict into normalized feature vector.

    Returns list of 8 normalized floats:
    [temp_min/40, temp_max/40, temp_media/40, temp_sorteio/40,
     precip_media/100, precip_sorteio/100, wcode_sorteio/99, wcode_dominant/99]

    Missing values become 0.0 (graceful degradation).
    """
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


def get_climate_for_draws(draws) -> List[Dict[int, float]]:
    """Get normalized climate features aligned with a list of Draw objects.

    Args:
        draws: list of Draw objects (must have .concurso attribute)

    Returns:
        List of dicts {concurso: normalized_features_list}
        Draws without climate data get empty dict.
    """
    climate_map = load_all_climate()
    result = []
    for draw in draws:
        if draw.concurso in climate_map:
            features = normalize_climate(climate_map[draw.concurso])
            result.append({
                "concurso": draw.concurso,
                "features": features,
            })
        else:
            result.append({
                "concurso": draw.concurso,
                "features": [],
            })
    return result


def _processar_resumo(hourly: Dict) -> Dict:
    """Calcula resumo diário a partir dos dados hourly."""
    temps = [t for t in hourly.get("temperature_2m", []) if t is not None]
    precip = [p for p in hourly.get("precipitation_probability", []) if p is not None]
    codes = [c for c in hourly.get("weathercode", []) if c is not None]

    if not temps and not precip and not codes:
        return {}

    hora_sorteio_idx = 20
    all_temps = hourly.get("temperature_2m", [])
    all_precip = hourly.get("precipitation_probability", [])
    all_codes = hourly.get("weathercode", [])

    temp_sorteio = all_temps[hora_sorteio_idx] if len(all_temps) > hora_sorteio_idx and all_temps[hora_sorteio_idx] is not None else None
    precip_sorteio = all_precip[hora_sorteio_idx] if len(all_precip) > hora_sorteio_idx and all_precip[hora_sorteio_idx] is not None else None
    code_sorteio = all_codes[hora_sorteio_idx] if len(all_codes) > hora_sorteio_idx and all_codes[hora_sorteio_idx] is not None else None

    code_counts = {}
    for c in all_codes:
        if c is not None:
            code_counts[c] = code_counts.get(c, 0) + 1
    code_dominante = max(code_counts, key=code_counts.get) if code_counts else None

    CODIGO_CLIMA = {
        0: "Céu limpo", 1: "Principalmente limpo", 2: "Parcialmente nublado",
        3: "Nublado", 45: "Neblina", 48: "Neblina com geada",
        51: "Garoa leve", 53: "Garoa moderada", 55: "Garoa densa",
        56: "Garoa congelante leve", 57: "Garoa congelante densa",
        61: "Chuva leve", 63: "Chuva moderada", 65: "Chuva forte",
        66: "Chuva congelante leve", 67: "Chuva congelante forte",
        71: "Neve leve", 73: "Neve moderada", 75: "Neve forte",
        77: "Grãos de neve",
        80: "Pancadas leves", 81: "Pancadas moderadas", 82: "Pancadas fortes",
        85: "Pancadas de neve leves", 86: "Pancadas de neve fortes",
        95: "Trovoada", 96: "Trovoada com granizo leve",
        99: "Trovoada com granizo forte",
    }

    return {
        "temp_min": round(min(temps), 1) if temps else None,
        "temp_max": round(max(temps), 1) if temps else None,
        "temp_media": round(sum(temps) / len(temps), 1) if temps else None,
        "precipitacao_media": round(sum(precip) / len(precip), 1) if precip else None,
        "temp_sorteio": temp_sorteio,
        "precipitacao_sorteio": precip_sorteio,
        "weathercode_sorteio": code_sorteio,
        "weathercode_dominante": code_dominante,
        "condicao_sorteio": CODIGO_CLIMA.get(code_sorteio, "Desconhecida") if code_sorteio is not None else None,
        "condicao_dominante": CODIGO_CLIMA.get(code_dominante, "Desconhecida") if code_dominante is not None else None,
    }


def fetch_climate_from_api(date_str: str) -> Optional[Dict]:
    """Fetch climate data from Open-Meteo API for a single date.

    Args:
        date_str: Date in YYYY-MM-DD format.

    Returns:
        Resumo dict with climate summary, or None on error.
    """
    global _last_fetch_time

    now = time.time()
    wait = DELAY_REQUISICOES - (now - _last_fetch_time)
    if wait > 0:
        time.sleep(wait)

    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "hourly": "temperature_2m,precipitation_probability,weathercode",
        "start_date": date_str,
        "end_date": date_str,
        "timezone": TIMEZONE,
    }

    try:
        resp = requests.get(API_URL, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        hourly = data.get("hourly", {})
        resumo = _processar_resumo(hourly)
        _last_fetch_time = time.time()
        return resumo
    except requests.exceptions.RequestException as e:
        logger.warning("API fetch failed for %s: %s", date_str, e)
        _last_fetch_time = time.time()
        return None
    except json.JSONDecodeError as e:
        logger.warning("JSON decode error for %s: %s", date_str, e)
        _last_fetch_time = time.time()
        return None


def save_fetched_climate(concurso: int, date: str, resumo: Dict, hourly: Optional[Dict] = None) -> None:
    """Save fetched climate data to local JSON file.

    Args:
        concurso: Contest number.
        date: Date in YYYY-MM-DD format.
        resumo: Climate summary dict.
        hourly: Optional hourly data from API response.
    """
    DIRETORIO_CLIMA.mkdir(parents=True, exist_ok=True)

    payload = {
        "concurso": concurso,
        "data": date,
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "timezone": TIMEZONE,
        "hourly_units": {
            "time": "iso8601",
            "temperature_2m": "°C",
            "precipitation_probability": "%",
            "weathercode": "wmo code",
        },
        "hourly": hourly or {},
        "resumo": resumo,
    }

    nome_arquivo = f"clima_concurso{concurso}-{date}.json"
    caminho = DIRETORIO_CLIMA / nome_arquivo

    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    logger.info("Saved climate data: %s", nome_arquivo)


def get_or_fetch_climate(concurso: int, date_str: str) -> Optional[Dict]:
    """Get climate data from cache/file, or fetch from API if missing.

    Checks local files first, then in-memory cache. If not found,
    fetches from Open-Meteo API and saves locally.

    Args:
        concurso: Contest number.
        date_str: Date in YYYY-MM-DD format.

    Returns:
        Resumo dict with climate summary, or None if all attempts fail.
    """
    if concurso in _local_cache:
        cached = _local_cache[concurso]
        return cached if not cached.get("_no_data") else None

    nome_arquivo = f"clima_concurso{concurso}-{date_str}.json"
    caminho = DIRETORIO_CLIMA / nome_arquivo

    if caminho.exists():
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                data = json.load(f)
            resumo = data.get("resumo", {})
            if resumo:
                _local_cache[concurso] = resumo
                return resumo
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("Corrupt climate file %s: %s", nome_arquivo, e)

    if date_str < _API_START_DATE:
        logger.debug("Date %s before API data range (%s), skipping", date_str, _API_START_DATE)
        _local_cache[concurso] = _NO_DATA_MARKER
        return None

    logger.info("Fetching climate from API: concurso %s (%s)", concurso, date_str)
    resumo = fetch_climate_from_api(date_str)

    if resumo:
        _local_cache[concurso] = resumo
        save_fetched_climate(concurso, date_str, resumo)
        return resumo

    logger.warning("Could not get climate data for concurso %s (%s)", concurso, date_str)
    _local_cache[concurso] = _NO_DATA_MARKER
    return None
