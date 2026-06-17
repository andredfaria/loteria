#!/usr/bin/env python3
"""Analisa métricas de ganhadores (15 e 14 acertos) e frequência de números."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from lotofacil.infra.config import DADOS_DIR


def load_all_draws() -> list[dict]:
    draws = []
    for f in sorted(DADOS_DIR.glob("concurso_*.json"), key=lambda p: int(p.stem.split("_")[1])):
        raw = json.loads(f.read_text())
        draws.append(raw)
    return draws


def extract_premiacao(premiacoes: list, faixa: int) -> dict | None:
    for p in premiacoes:
        if p["faixa"] == faixa:
            return p
    return None


def analyze(draws: list[dict]):
    faixa15_all = []
    faixa14_all = []
    concursos_top15 = []
    concursos_top14 = []
    number_counter = Counter()
    total = len(draws)

    for d in draws:
        premiacoes = d.get("premiacoes", [])
        concurso = d["concurso"]
        dezenas = [int(n) for n in d["dezenas"]]

        for n in dezenas:
            number_counter[n] += 1

        p15 = extract_premiacao(premiacoes, 1)
        p14 = extract_premiacao(premiacoes, 2)

        if p15:
            faixa15_all.append((concurso, p15["ganhadores"], p15["valorPremio"], dezenas))
        if p14:
            faixa14_all.append((concurso, p14["ganhadores"], p14["valorPremio"], dezenas))

    # ---- FAUXA 15 ----
    faixa15_all.sort(key=lambda x: x[1], reverse=True)
    concursos_top15 = faixa15_all[:10]
    ganhadores15 = [g for _, g, _, _ in faixa15_all]
    premios15 = [p for _, _, p, _ in faixa15_all]
    nao_acumulou_15 = [g for g in ganhadores15 if g > 0]

    # ---- FAIXA 14 ----
    faixa14_all.sort(key=lambda x: x[1], reverse=True)
    concursos_top14 = faixa14_all[:10]
    ganhadores14 = [g for _, g, _, _ in faixa14_all]

    return {
        "total": total,
        "faixa15_all": faixa15_all,
        "faixa14_all": faixa14_all,
        "concursos_top15": concursos_top15,
        "concursos_top14": concursos_top14,
        "ganhadores15": ganhadores15,
        "premios15": premios15,
        "ganhadores14": ganhadores14,
        "nao_acumulou_15": nao_acumulou_15,
        "number_counter": number_counter,
    }


def print_analysis(result: dict):
    total = result["total"]
    g15 = result["ganhadores15"]
    g14 = result["ganhadores14"]
    nao_acumulou = result["nao_acumulou_15"]
    nc15 = result["concursos_top15"]
    nc14 = result["concursos_top14"]
    counter = result["number_counter"]

    print("=" * 70)
    print(f"  ANÁLISE DE GANHADORES — LOTOFÁCIL (1–{total})")
    print("=" * 70)

    # ---- 15 ACERTOS ----
    print(f"\n{'─'*70}")
    print("  FAIXA 15 ACERTOS")
    print(f"{'─'*70}")
    print(f"  Total de concursos:          {total}")
    print(f"  Concursos c/ ganhadores:     {len(nao_acumulou)} ({len(nao_acumulou)/total*100:.1f}%)")
    print(f"  Concursos acumulados (0 gan):{len(g15) - len(nao_acumulou)}")
    if nao_acumulou:
        print(f"  Média de ganhadores (qdo paga): {sum(nao_acumulou)/len(nao_acumulou):.1f}")
        print(f"  Mediana de ganhadores:         {sorted(nao_acumulou)[len(nao_acumulou)//2]}")
    print(f"  Máximo de ganhadores:         {max(g15)} (concurso {result['faixa15_all'][0][0]})")
    print(f"  Mínimo de ganhadores (>0):    {min(nao_acumulou) if nao_acumulou else 'N/A'}")

    print(f"\n  ▶ Top 10 concursos com MAIS ganhadores (15 acertos):")
    print(f"  {'Concurso':>8}  {'Ganhadores':>10}  {'Prêmio':>15}  {'Dezenas':>40}")
    print(f"  {'─'*8}  {'─'*10}  {'─'*15}  {'─'*40}")
    for c, g, p, dezs in nc15:
        dezs_str = ",".join(f"{d:02d}" for d in sorted(dezs))
        premio_str = f"R$ {p:,.2f}" if p > 0 else "Acumulou"
        print(f"  {c:>8}  {g:>10}  {premio_str:>15}  {dezs_str}")

    # ---- 14 ACERTOS ----
    print(f"\n{'─'*70}")
    print("  FAIXA 14 ACERTOS")
    print(f"{'─'*70}")
    print(f"  Média de ganhadores:      {sum(g14)/len(g14):.1f}")
    print(f"  Mediana de ganhadores:    {sorted(g14)[len(g14)//2]}")
    print(f"  Máximo de ganhadores:     {max(g14)} (concurso {result['faixa14_all'][0][0]})")

    print(f"\n  ▶ Top 10 concursos com MAIS ganhadores (14 acertos):")
    print(f"  {'Concurso':>8}  {'Ganhadores':>10}  {'Prêmio':>15}  {'Dezenas':>40}")
    print(f"  {'─'*8}  {'─'*10}  {'─'*15}  {'─'*40}")
    for c, g, p, dezs in nc14:
        dezs_str = ",".join(f"{d:02d}" for d in sorted(dezs))
        premio_str = f"R$ {p:,.2f}" if p > 0 else "N/A"
        print(f"  {c:>8}  {g:>10}  {premio_str:>15}  {dezs_str}")

    # ---- FREQUÊNCIA DOS NÚMEROS ----
    print(f"\n{'─'*70}")
    print("  FREQUÊNCIA DOS NÚMEROS (1–25) — HISTÓRICO COMPLETO")
    print(f"{'─'*70}")
    print(f"  {'Número':>6}  {'Vezes':>6}  {'Freq%':>7}  {'Barra':>30}")
    for num in range(1, 26):
        count = counter[num]
        pct = count / total * 100
        bar = "█" * int(pct / 2)
        print(f"  {num:>6}  {count:>6}  {pct:>6.2f}%  {bar}")

    # ---- CONCURSOS ONDE MAIS GENTE GANHOU (15 e 14 juntos) ----
    print(f"\n{'─'*70}")
    print("  CONCURSOS ONDE MAIS GENTE GANHOU (15 + 14 combinado)")
    print(f"{'─'*70}")
    combined = []
    for d in result["faixa15_all"]:
        concurso = d[0]
        g15 = d[1]
        # find 14 for same contest
        g14_val = 0
        for dd in result["faixa14_all"]:
            if dd[0] == concurso:
                g14_val = dd[1]
                break
        combined.append((concurso, g15, g14_val, g15 + g14_val, d[3]))

    combined.sort(key=lambda x: x[3], reverse=True)
    print(f"  {'Concurso':>8}  {'Ganh 15':>8}  {'Ganh 14':>8}  {'Total':>8}  {'Dezenas':>40}")
    print(f"  {'─'*8}  {'─'*8}  {'─'*8}  {'─'*8}  {'─'*40}")
    for c, g15v, g14v, tot, dezs in combined[:10]:
        dezs_str = ",".join(f"{d:02d}" for d in sorted(dezs))
        print(f"  {c:>8}  {g15v:>8}  {g14v:>8}  {tot:>8}  {dezs_str}")

    # ---- NÚMEROS QUE MAIS SAÍRAM NOS TOP CONCURSOS ----
    print(f"\n{'─'*70}")
    print("  NÚMEROS QUE MAIS APARECEM NOS TOP 20 CONCURSOS (mais ganhadores 15)")
    print(f"{'─'*70}")
    top20_concs = result["faixa15_all"][:20]
    top_counter = Counter()
    for _, _, _, dezs in top20_concs:
        for n in dezs:
            top_counter[n] += 1
    for num, count in top_counter.most_common(15):
        print(f"  Número {num:>2}: apareceu em {count}/{len(top20_concs)} concursos ({count/len(top20_concs)*100:.0f}%)")

    print()
    print("=" * 70)


def main():
    print("Carregando dados...")
    draws = load_all_draws()
    print(f"  {len(draws)} concursos carregados\n")

    result = analyze(draws)
    print_analysis(result)


if __name__ == "__main__":
    main()
