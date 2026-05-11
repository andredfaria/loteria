#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Busca dados climáticos via Open-Meteo API e vincula aos concursos da Lotofácil.
Salva em dados/clima/clima_concurso{N}-{YYYY-MM-DD}.json

Uso:
  python src/coleta/busca_clima.py              # últimos 50 concursos
  python src/coleta/busca_clima.py --ultimos 20  # últimos N concursos
  python src/coleta/busca_clima.py --todos       # todos os concursos
  python src/coleta/busca_clima.py --concurso 3650  # concurso específico
  python src/coleta/busca_clima.py --data 2026-05-04  # data avulsa (sem vínculo)
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests

# Configurações
API_URL = "https://api.open-meteo.com/v1/forecast"
LATITUDE = -23.55
LONGITUDE = -46.63
TIMEZONE = "America/Sao_Paulo"
DELAY_REQUISICOES = 0.8  # segundos entre requisições

DIRETORIO_BASE = Path(__file__).resolve().parent.parent.parent
DIRETORIO_DADOS = DIRETORIO_BASE / "dados"
DIRETORIO_CLIMA = DIRETORIO_BASE / "dados" / "clima"

# WMO Weather interpretation codes
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


def converter_data(data_str: str) -> str:
    """Converte DD/MM/YYYY para YYYY-MM-DD."""
    if not data_str:
        return ""
    try:
        return datetime.strptime(data_str.strip(), "%d/%m/%Y").strftime("%Y-%m-%d")
    except ValueError:
        return ""


def listar_concursos(
    inicio: Optional[int] = None, fim: Optional[int] = None
) -> List[Dict]:
    """Lista concursos existentes com número e data."""
    concursos = []
    for f in DIRETORIO_DADOS.glob("concurso_*.json"):
        try:
            num = int(f.stem.split("_")[1])
            if inicio is not None and num < inicio:
                continue
            if fim is not None and num > fim:
                continue
            with open(f, "r", encoding="utf-8") as fh:
                dados = json.load(fh)
            data_iso = converter_data(dados.get("data", ""))
            if data_iso:
                concursos.append({"concurso": num, "data": data_iso})
        except (IndexError, ValueError, json.JSONDecodeError):
            continue
    return sorted(concursos, key=lambda c: c["concurso"])


def buscar_clima_api(data: str) -> Optional[Dict]:
    """Busca dados climáticos da Open-Meteo para uma data."""
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "hourly": "temperature_2m,precipitation_probability,weathercode",
        "start_date": data,
        "end_date": data,
        "timezone": TIMEZONE,
    }
    try:
        resp = requests.get(API_URL, params=params, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        print(f"  Erro na requisição para {data}: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"  Erro ao decodificar JSON para {data}: {e}")
        return None


def processar_resumo(hourly: Dict) -> Dict:
    """Calcula resumo diário a partir dos dados hourly."""
    temps = hourly.get("temperature_2m", [])
    precip = hourly.get("precipitation_probability", [])
    codes = hourly.get("weathercode", [])

# Horário do sorteio: ~21h BRT (índice 21)
hora_sorteio_idx = 21
    temp_sorteio = temps[hora_sorteio_idx] if len(temps) > hora_sorteio_idx else None
    precip_sorteio = precip[hora_sorteio_idx] if len(precip) > hora_sorteio_idx else None
    code_sorteio = codes[hora_sorteio_idx] if len(codes) > hora_sorteio_idx else None

    # Código mais frequente no dia
    code_counts = {}
    for c in codes:
        code_counts[c] = code_counts.get(c, 0) + 1
    code_dominante = max(code_counts, key=code_counts.get) if code_counts else None

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


def salvar_clima(dados_clima: Dict, concurso: int, data: str) -> str:
    """Salva dados climáticos vinculados ao concurso."""
    DIRETORIO_CLIMA.mkdir(parents=True, exist_ok=True)
    nome_arquivo = f"clima_concurso{concurso}-{data}.json"
    caminho = DIRETORIO_CLIMA / nome_arquivo

    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados_clima, f, ensure_ascii=False, indent=2)

    return str(caminho)


def montar_payload(api_resp: Dict, concurso: int, data: str) -> Dict:
    """Monta o payload final para salvar."""
    hourly = api_resp.get("hourly", {})
    return {
        "concurso": concurso,
        "data": data,
        "latitude": api_resp.get("latitude", LATITUDE),
        "longitude": api_resp.get("longitude", LONGITUDE),
        "timezone": api_resp.get("timezone", TIMEZONE),
        "hourly_units": api_resp.get("hourly_units", {}),
        "hourly": hourly,
        "resumo": processar_resumo(hourly),
    }


def buscar_para_concursos(concursos: List[Dict]) -> Tuple[int, int, int]:
    """Busca clima para lista de concursos. Retorna (sucessos, falhas, ja_existentes)."""
    sucessos = 0
    falhas = 0
    ja_existentes = 0

    total = len(concursos)
    for i, conc in enumerate(concursos, 1):
        num = conc["concurso"]
        data = conc["data"]
        nome_arquivo = f"clima_concurso{num}-{data}.json"
        caminho = DIRETORIO_CLIMA / nome_arquivo

        print(f"[{i}/{total}] Concurso {num} ({data})...", end=" ")

        if caminho.exists():
            print("Já existe")
            ja_existentes += 1
            continue

        clima_raw = buscar_clima_api(data)
        if clima_raw is None:
            print("Falhou")
            falhas += 1
            continue

        payload = montar_payload(clima_raw, num, data)
        salvar_clima(payload, num, data)
        resumo = payload["resumo"]
        print(f"Salvo — temp: {resumo['temp_min']:.0f}–{resumo['temp_max']:.0f}°C, "
              f"chuva: {resumo['precipitacao_sorteio']}%, "
              f"condição: {resumo['condicao_sorteio']}")
        sucessos += 1

        if i < total:
            time.sleep(DELAY_REQUISICOES)

    return sucessos, falhas, ja_existentes


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Busca dados climáticos da Open-Meteo vinculados aos concursos da Lotofácil"
    )
    grupo = parser.add_mutually_exclusive_group()
    grupo.add_argument("--todos", action="store_true",
                       help="Busca clima de todos os concursos existentes")
    grupo.add_argument("--ultimos", type=int, nargs="?", const=50, default=None,
                       help="Busca clima dos últimos N concursos (padrão: 50)")
    grupo.add_argument("--concurso", type=int, default=None,
                       help="Busca clima de um concurso específico")
    grupo.add_argument("--data", type=str, default=None,
                       help="Busca clima para uma data (YYYY-MM-DD, sem vínculo com concurso)")
    return parser.parse_args()


def main():
    args = parse_args()

    if args.data:
        print(f"Buscando clima para {args.data} (sem vínculo)...")
        clima_raw = buscar_clima_api(args.data)
        if clima_raw:
            payload = montar_payload(clima_raw, 0, args.data)
            DIRETORIO_CLIMA.mkdir(parents=True, exist_ok=True)
            caminho = DIRETORIO_CLIMA / f"clima_{args.data}.json"
            with open(caminho, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            print(f"Salvo em {caminho}")
            res = payload["resumo"]
            print(f"  Temp: {res['temp_min']:.0f}–{res['temp_max']:.0f}°C (média: {res['temp_media']:.0f}°C)")
            print(f"  Chuva sorteio: {res['precipitacao_sorteio']}%")
            print(f"  Condição: {res['condicao_sorteio']}")
        return

    if args.concurso:
        concursos = listar_concursos(inicio=args.concurso, fim=args.concurso)
        if not concursos:
            print(f"Concurso {args.concurso} não encontrado em {DIRETORIO_DADOS}")
            sys.exit(1)
    elif args.todos:
        concursos = listar_concursos()
    else:
        ultimos = args.ultimos if args.ultimos is not None else 50
        all_concursos = listar_concursos()
        concursos = all_concursos[-ultimos:] if len(all_concursos) > ultimos else all_concursos

    if not concursos:
        print("Nenhum concurso encontrado.")
        sys.exit(1)

    print("=" * 60)
    print("Buscador de Clima — Lotofácil (Open-Meteo)")
    print(f"Local: São Paulo, SP ({LATITUDE}, {LONGITUDE})")
    print(f"Concursos: {concursos[0]['concurso']} até {concursos[-1]['concurso']}")
    print(f"Total: {len(concursos)}")
    print("=" * 60)
    print()

    sucessos, falhas, ja_existentes = buscar_para_concursos(concursos)

    print()
    print("=" * 60)
    print(f"Sucessos: {sucessos}")
    print(f"Já existentes: {ja_existentes}")
    print(f"Falhas: {falhas}")
    print("=" * 60)


if __name__ == "__main__":
    main()
