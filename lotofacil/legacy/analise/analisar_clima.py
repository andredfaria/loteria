#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Análise de correlação entre dados climáticos e números sorteados na Lotofácil.

Cruza dados de clima (temperatura, precipitação) com dezenas sorteadas
e exibe padrões observados.

Uso:
  python src/analise/analisar_clima.py
  python src/analise/analisar_clima.py --minimo 30  # mínimo de concursos com clima
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

DIRETORIO_BASE = Path(__file__).resolve().parent.parent.parent
DIRETORIO_DADOS = DIRETORIO_BASE / "dados"
DIRETORIO_CLIMA = DIRETORIO_BASE / "dados" / "clima"


def carregar_concursos() -> Dict[int, Dict]:
    """Carrega todos os concursos existentes."""
    concursos = {}
    for f in DIRETORIO_DADOS.glob("concurso_*.json"):
        try:
            num = int(f.stem.split("_")[1])
            with open(f, "r", encoding="utf-8") as fh:
                dados = json.load(fh)
            concursos[num] = dados
        except (IndexError, ValueError, json.JSONDecodeError):
            continue
    return concursos


def carregar_climas() -> List[Dict]:
    """Carrega todos os dados climáticos vinculados a concursos."""
    climas = []
    for f in sorted(DIRETORIO_CLIMA.glob("clima_concurso*.json")):
        try:
            with open(f, "r", encoding="utf-8") as fh:
                dados = json.load(fh)
            if dados.get("concurso") and dados.get("concurso") > 0:
                climas.append(dados)
        except (json.JSONDecodeError, KeyError):
            continue
    return climas


def cruzar_dados(concursos: Dict[int, Dict], climas: List[Dict]) -> List[Dict]:
    """Cruza clima com concurso pela data."""
    cruzados = []
    for clima in climas:
        num = clima.get("concurso")
        if num in concursos:
            cruzados.append({
                "concurso": num,
                "data": clima.get("data"),
                "dezenas": [int(d) for d in concursos[num].get("dezenas", [])],
                "resumo": clima.get("resumo", {}),
            })
    return sorted(cruzados, key=lambda c: c["concurso"])


def analisar_temperatura(cruzados: List[Dict]) -> Dict:
    """Analisa frequência de dezenas por faixa de temperatura."""
    faixas = {
        "frio (< 18°C)": [],
        "agradável (18-24°C)": [],
        "quente (> 24°C)": [],
    }

    for c in cruzados:
        temp = c["resumo"].get("temp_sorteio")
        if temp is None:
            temp = c["resumo"].get("temp_media")
        if temp is None:
            continue

        if temp < 18:
            faixas["frio (< 18°C)"].extend(c["dezenas"])
        elif temp <= 24:
            faixas["agradável (18-24°C)"].extend(c["dezenas"])
        else:
            faixas["quente (> 24°C)"].extend(c["dezenas"])

    resultado = {}
    for faixa, dezenas in faixas.items():
        if not dezenas:
            continue
        freq = defaultdict(int)
        for d in dezenas:
            freq[d] += 1
        total_sorteios = len(dezenas) // 15
        freq_pct = {k: round(v / total_sorteios * 100, 1) for k, v in freq.items()}
        mais_freq = sorted(freq_pct.items(), key=lambda x: x[1], reverse=True)[:5]
        menos_freq = sorted(freq_pct.items(), key=lambda x: x[1])[:5]
        resultado[faixa] = {
            "sorteios": total_sorteios,
            "mais_frequentes": mais_freq,
            "menos_frequentes": menos_freq,
        }

    return resultado


def analisar_chuva(cruzados: List[Dict]) -> Dict:
    """Analisa frequência de dezenas por probabilidade de chuva."""
    faixas = {
        "sem chuva (0-20%)": [],
        "chuva baixa (20-50%)": [],
        "chuva alta (> 50%)": [],
    }

    for c in cruzados:
        precip = c["resumo"].get("precipitacao_sorteio")
        if precip is None:
            precip = c["resumo"].get("precipitacao_media", 50)

        if precip <= 20:
            faixas["sem chuva (0-20%)"].extend(c["dezenas"])
        elif precip <= 50:
            faixas["chuva baixa (20-50%)"].extend(c["dezenas"])
        else:
            faixas["chuva alta (> 50%)"].extend(c["dezenas"])

    resultado = {}
    for faixa, dezenas in faixas.items():
        if not dezenas:
            continue
        freq = defaultdict(int)
        for d in dezenas:
            freq[d] += 1
        total_sorteios = len(dezenas) // 15
        freq_pct = {k: round(v / total_sorteios * 100, 1) for k, v in freq.items()}
        mais_freq = sorted(freq_pct.items(), key=lambda x: x[1], reverse=True)[:5]
        menos_freq = sorted(freq_pct.items(), key=lambda x: x[1])[:5]
        resultado[faixa] = {
            "sorteios": total_sorteios,
            "mais_frequentes": mais_freq,
            "menos_frequentes": menos_freq,
        }

    return resultado


def analisar_pares_impares(cruzados: List[Dict]) -> Dict:
    """Analisa distribuição pares/ímpares por condição climática."""
    condicoes = defaultdict(lambda: {"pares": 0, "impares": 0, "sorteios": 0})

    for c in cruzados:
        condicao = c["resumo"].get("condicao_sorteio", "Desconhecida")
        pares = sum(1 for d in c["dezenas"] if d % 2 == 0)
        impares = 15 - pares
        condicoes[condicao]["pares"] += pares
        condicoes[condicao]["impares"] += impares
        condicoes[condicao]["sorteios"] += 1

    resultado = {}
    for cond, stats in condicoes.items():
        total = stats["pares"] + stats["impares"]
        resultado[cond] = {
            "sorteios": stats["sorteios"],
            "pares_pct": round(stats["pares"] / total * 100, 1) if total else 0,
            "impares_pct": round(stats["impares"] / total * 100, 1) if total else 0,
        }

    return resultado


def exibir_resultados(analise_temp: Dict, analise_chuva: Dict,
                      analise_pares: Dict, total_cruzados: int):
    """Exibe relatório formatado no terminal."""
    sep = "=" * 60

    print(sep)
    print(f"Análise Clima vs Números — Lotofácil")
    print(f"Concursos com dados climáticos: {total_cruzados}")
    print(sep)

    print("\n🌡️ TEMPERATURA vs DEZENAS\n")
    for faixa, dados in analise_temp.items():
        print(f"  {faixa} ({dados['sorteios']} sorteios)")
        print(f"    + frequentes: {', '.join(f'{d}({p}%)' for d, p in dados['mais_frequentes'])}")
        print(f"    - frequentes: {', '.join(f'{d}({p}%)' for d, p in dados['menos_frequentes'])}")
        print()

    print("🌧️ CHUVA vs DEZENAS\n")
    for faixa, dados in analise_chuva.items():
        print(f"  {faixa} ({dados['sorteios']} sorteios)")
        print(f"    + frequentes: {', '.join(f'{d}({p}%)' for d, p in dados['mais_frequentes'])}")
        print(f"    - frequentes: {', '.join(f'{d}({p}%)' for d, p in dados['menos_frequentes'])}")
        print()

    print("⚖️ PARES/ÍMPARES vs CONDIÇÃO CLIMÁTICA\n")
    for cond, dados in analise_pares.items():
        print(f"  {cond} ({dados['sorteios']} sorteios)")
        print(f"    Pares: {dados['pares_pct']}% | Ímpares: {dados['impares_pct']}%")
        print()

    print(sep)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analisa correlação entre clima e números sorteados na Lotofácil"
    )
    parser.add_argument("--minimo", type=int, default=10,
                        help="Mínimo de concursos com clima para analisar (padrão: 10)")
    return parser.parse_args()


def main():
    args = parse_args()

    print("Carregando concursos...")
    concursos = carregar_concursos()
    print(f"  {len(concursos)} concursos encontrados")

    print("Carregando dados climáticos...")
    climas = carregar_climas()
    print(f"  {len(climas)} arquivos de clima encontrados")

    if len(climas) < args.minimo:
        print(f"\nDados insuficientes: {len(climas)} < {args.minimo} mínimo.")
        print("Execute: python src/coleta/busca_clima.py --todos")
        sys.exit(1)

    cruzados = cruzar_dados(concursos, climas)
    print(f"  {len(cruzados)} concursos cruzados com sucesso")

    if len(cruzados) < args.minimo:
        print(f"\nDados insuficientes após cruzamento: {len(cruzados)} < {args.minimo}")
        sys.exit(1)

    print("\nAnalisando...")
    analise_temp = analisar_temperatura(cruzados)
    analise_chuva = analisar_chuva(cruzados)
    analise_pares = analisar_pares_impares(cruzados)

    print()
    exibir_resultados(analise_temp, analise_chuva, analise_pares, len(cruzados))


if __name__ == "__main__":
    main()
