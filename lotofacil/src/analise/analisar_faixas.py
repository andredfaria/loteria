#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
src/analise/analisar_faixas.py — Análise de distribuição por faixas e temperatura dos números

Segue o mesmo padrão de ciclo_dezenas.py (argparse, lê concurso_N.json, saída stdout).
"""

import json
import os
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Tuple

DIRETORIO_DADOS = str(Path(__file__).resolve().parent.parent.parent / "dados")

FAIXAS = {
    "faixa_1_5":   list(range(1, 6)),
    "faixa_6_10":  list(range(6, 11)),
    "faixa_11_15": list(range(11, 16)),
    "faixa_16_20": list(range(16, 21)),
    "faixa_21_25": list(range(21, 26)),
}


def carregar_concurso(numero: int) -> Dict:
    """Carrega um concurso individual de dados/concurso_N.json."""
    arquivo = os.path.join(DIRETORIO_DADOS, f"concurso_{numero}.json")
    with open(arquivo, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return {
        "concurso": raw["concurso"],
        "dezenas": sorted([int(d) for d in raw["dezenas"]]),
    }


def carregar_todos_concursos() -> List[Dict]:
    """Carrega todos os concursos disponíveis em dados/."""
    dados_path = Path(DIRETORIO_DADOS)
    concursos = []
    for arquivo in dados_path.glob("concurso_*.json"):
        try:
            with open(arquivo, "r", encoding="utf-8") as f:
                raw = json.load(f)
            concursos.append({
                "concurso": raw["concurso"],
                "dezenas": sorted([int(d) for d in raw["dezenas"]]),
            })
        except Exception:
            continue
    concursos.sort(key=lambda x: x["concurso"])
    return concursos


def contar_por_faixa(dezenas: List[int]) -> Dict[str, int]:
    """Conta quantos dos 15 números caem em cada uma das 5 faixas."""
    return {nome: sum(1 for n in dezenas if n in faixa) for nome, faixa in FAIXAS.items()}


def analisar_distribuicao_historico(concursos: List[Dict]) -> Dict:
    """
    Agrega para todos os concursos:
    - mean, std, min, max por faixa
    - % dos concursos com >=2 números em TODAS as faixas
    """
    import math

    faixa_nomes = list(FAIXAS.keys())
    contagens_por_faixa = {nome: [] for nome in faixa_nomes}

    for c in concursos:
        fc = contar_por_faixa(c["dezenas"])
        for nome in faixa_nomes:
            contagens_por_faixa[nome].append(fc[nome])

    resultado = {}
    for nome in faixa_nomes:
        vals = contagens_por_faixa[nome]
        n = len(vals)
        mean = sum(vals) / n
        variance = sum((v - mean) ** 2 for v in vals) / n
        std = math.sqrt(variance)
        pct_ge2 = sum(1 for v in vals if v >= 2) / n * 100
        resultado[nome] = {
            "mean": mean,
            "std": std,
            "min": min(vals),
            "max": max(vals),
            "pct_ge2": pct_ge2,
        }

    # % dos concursos com >=2 em TODAS as faixas
    pct_todas = sum(
        1 for c in concursos
        if all(contar_por_faixa(c["dezenas"])[nome] >= 2 for nome in faixa_nomes)
    ) / len(concursos) * 100

    return {"por_faixa": resultado, "pct_todas_cobertas": pct_todas}


def calcular_temperatura_numero(numero: int, concursos: List[Dict], idx: int) -> str:
    """
    "quente": apareceu em >=3 dos últimos 5 draws (atraso <= 2 na janela k=5)
    "morno":  apareceu nos últimos 10 mas não nos últimos 3 (atraso 3-4)
    "frio":   ausente dos últimos 5+ draws (atraso >= 5)
    """
    # Calcular atraso
    atraso = None
    for dist in range(1, min(idx + 1, 11)):
        c_idx = idx - dist
        if c_idx < 0:
            break
        if numero in concursos[c_idx]["dezenas"]:
            atraso = dist - 1
            break
    if atraso is None:
        atraso = 10

    if atraso <= 2:
        return "quente"
    elif atraso <= 4:
        return "morno"
    else:
        return "frio"


def analisar_temperatura_atual(concursos: List[Dict]) -> Dict[int, Dict]:
    """
    Para o concurso mais recente: retorna {num: {"temperatura", "atraso", "freq_k10"}}
    para cada número 1-25.
    """
    idx = len(concursos)  # Ponto após o último concurso
    window_k10 = concursos[max(0, idx - 10):idx]

    freq_k10 = {n: 0 for n in range(1, 26)}
    for c in window_k10:
        for d in c["dezenas"]:
            freq_k10[d] += 1

    resultado = {}
    for n in range(1, 26):
        # Calcular atraso real
        atraso = 20
        for dist in range(1, min(idx + 1, 21)):
            c_idx = idx - dist
            if c_idx < 0:
                break
            if n in concursos[c_idx]["dezenas"]:
                atraso = dist - 1
                break

        if atraso <= 2:
            temp = "quente"
        elif atraso <= 4:
            temp = "morno"
        else:
            temp = "frio"

        resultado[n] = {
            "temperatura": temp,
            "atraso": atraso,
            "freq_k10": freq_k10[n],
        }

    return resultado


def recomendar_jogo_por_faixas(temperatura: Dict[int, Dict], target_por_faixa: int = 3) -> List[int]:
    """
    Sugere 15 números: ~3 por faixa.
    Prioridade dentro de cada faixa: quente > morno > frio.
    Desempate por freq_k10 descendente.
    """
    temp_ordem = {"quente": 0, "morno": 1, "frio": 2}
    jogo = []

    for nome, numeros_faixa in FAIXAS.items():
        candidatos = sorted(
            numeros_faixa,
            key=lambda n: (temp_ordem[temperatura[n]["temperatura"]], -temperatura[n]["freq_k10"])
        )
        selecionados = candidatos[:target_por_faixa]
        jogo.extend(selecionados)

    return sorted(jogo)


def main():
    parser = argparse.ArgumentParser(description="Análise de faixas e temperatura da Lotofácil")
    parser.add_argument("--concurso", type=int, default=None,
                        help="Número do concurso de referência (padrão: mais recente)")
    args = parser.parse_args()

    concursos = carregar_todos_concursos()
    if not concursos:
        print("Nenhum dado encontrado em dados/")
        return

    ultimo_num = concursos[-1]["concurso"]
    concurso_ref = args.concurso or ultimo_num

    print("=" * 60)
    print(f"ANÁLISE DE FAIXAS E TEMPERATURA — Lotofácil")
    print(f"Concurso de referência: {concurso_ref}")
    print(f"Total de concursos carregados: {len(concursos)}")
    print("=" * 60)

    # --- Distribuição histórica ---
    dist = analisar_distribuicao_historico(concursos)
    print("\nDISTRIBUIÇÃO POR FAIXAS (histórico completo):")
    faixa_labels = {
        "faixa_1_5":   "01-05",
        "faixa_6_10":  "06-10",
        "faixa_11_15": "11-15",
        "faixa_16_20": "16-20",
        "faixa_21_25": "21-25",
    }
    for nome, label in faixa_labels.items():
        info = dist["por_faixa"][nome]
        print(f"  Faixa {label}: média {info['mean']:.1f}, std {info['std']:.1f} | "
              f"min {info['min']}, max {info['max']} | "
              f">= 2 nums em {info['pct_ge2']:.1f}% dos concursos")
    print(f"\n  Concursos com >=2 em TODAS as faixas: {dist['pct_todas_cobertas']:.1f}%")

    # --- Temperatura atual ---
    temperatura = analisar_temperatura_atual(concursos)
    print(f"\nTEMPERATURA DOS NÚMEROS (após concurso {ultimo_num}):")

    quentes = [n for n in range(1, 26) if temperatura[n]["temperatura"] == "quente"]
    mornos  = [n for n in range(1, 26) if temperatura[n]["temperatura"] == "morno"]
    frios   = [n for n in range(1, 26) if temperatura[n]["temperatura"] == "frio"]

    fmt = lambda lst: ", ".join(f"{n:02d}" for n in lst)
    print(f"  Quentes (atraso <=2): {fmt(quentes)}")
    print(f"  Mornos  (atraso 3-4): {fmt(mornos)}")
    print(f"  Frios   (atraso >=5): {fmt(frios)}")

    print("\n  Detalhes por número:")
    for n in range(1, 26):
        info = temperatura[n]
        print(f"    {n:02d}: {info['temperatura']:7s} | atraso={info['atraso']:2d} | "
              f"freq_k10={info['freq_k10']}")

    # --- Jogo recomendado ---
    jogo_rec = recomendar_jogo_por_faixas(temperatura)
    print(f"\nJOGO RECOMENDADO (3 por faixa, prioridade: quente > morno > frio):")
    for nome, label in faixa_labels.items():
        nums_faixa = [n for n in jogo_rec if n in FAIXAS[nome]]
        print(f"  Faixa {label}: {fmt(nums_faixa)}")
    print(f"\n  Jogo completo: {fmt(jogo_rec)}")
    print(f"  Soma: {sum(jogo_rec)} | Pares: {sum(1 for n in jogo_rec if n % 2 == 0)}")
    print()


if __name__ == "__main__":
    main()
