"""Find 15-number combos with most 11/12/13 hits but ZERO 15-acertos (never drawn)."""

import heapq, itertools, sys, time
from pathlib import Path
from collections import Counter

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC_DIR))

from lotofacil.infra.config import DADOS_DIR
from lotofacil.infra.dados.leitor import load_draws


def main():
    draws = load_draws(DADOS_DIR)
    total = len(draws)
    print(f"Carregados {total} sorteios\n")

    counter = Counter()
    for d in draws:
        counter.update(d.dezenas)
    freq = [0] * 26
    for n, c in counter.most_common():
        freq[n] = c

    def sum_freq(c):
        return sum(freq[n] for n in c)

    N_CANDIDATOS = 2000
    print(f"Gerando top {N_CANDIDATOS} candidatos...")
    top = heapq.nlargest(N_CANDIDATOS, itertools.combinations(range(1, 26), 15), key=sum_freq)
    print(f"Avaliando contra {total} sorteios...")
    t0 = time.time()

    resultados = []
    for combo in top:
        s = set(combo)
        h = Counter()
        for d in draws:
            k = len(s & set(d.dezenas))
            if k >= 11:
                h[k] += 1
        resultados.append((combo, h))

    filtrados = [r for r in resultados if r[1][15] == 0]
    print(f"Tempo: {time.time()-t0:.1f}s | Com 15=0: {len(filtrados)}/{len(resultados)}\n")

    # ── Ranking 1: mais 11+12+13 ──
    rank1 = sorted(filtrados, key=lambda r: r[1][11]+r[1][12]+r[1][13], reverse=True)[:3]
    # ── Ranking 2: prioriza 13 > 12 > 11 ──
    rank2 = sorted(filtrados, key=lambda r: (r[1][13], r[1][12], r[1][11]), reverse=True)[:3]
    # ── Ranking 3: maior ROI (13+14 com peso) ──
    rank3 = sorted(filtrados, key=lambda r: r[1][13]*35 + r[1][12]*14 + r[1][11]*7, reverse=True)[:3]

    for titulo, dados, label in [
        ("MAIS 11+12+13 ACERTOS (NUNCA SORTEADOS)", rank1, "11+12+13"),
        ("PRIORIZANDO 13 > 12 > 11 (NUNCA SORTEADOS)", rank2, "13"),
        ("MAIOR PREMIAÇÃO (NUNCA SORTEADOS)", rank3, "Prêmio"),
    ]:
        print(f"{'='*90}")
        print(f"{f'🏆  {titulo}':^90}")
        print(f"{'='*90}")
        for rank, (combo, h) in enumerate(dados, 1):
            custo = total * 3.50
            premio = h[11]*7 + h[12]*14 + h[13]*35 + h[14]*2000
            roi = premio / custo * 100
            hdr = "  🏆 CAMPEÃO" if rank == 1 else f"  #{rank}"
            print(f"\n  {hdr}")
            print(f"  {'─'*70}")
            print(f"  Números: {sorted(combo)}")
            print(f"  11: {h[11]:>4}x | 12: {h[12]:>4}x | 13: {h[13]:>4}x | 14: {h[14]:>4}x | 15: {h[15]:>4}x")
            s = h[11]+h[12]+h[13]
            print(f"  11+12+13: {s}x ({s/total*100:.2f}%) | Prêmio: R$ {premio:>8,.2f} | ROI: {roi:>5.1f}%")

    # ── Top 10 geral por ROI ──
    print(f"\n{'='*90}")
    print(f"{'📊  TOP 10 — ROI (NUNCA SORTEADOS)':^90}")
    print(f"{'='*90}")
    top10_roi = sorted(filtrados, key=lambda r: r[1][11]*7+r[1][12]*14+r[1][13]*35+r[1][14]*2000, reverse=True)[:10]
    for rank, (combo, h) in enumerate(top10_roi, 1):
        premio = h[11]*7 + h[12]*14 + h[13]*35 + h[14]*2000
        roi = premio / (total * 3.50) * 100
        print(f"  {rank:2d}. {sorted(combo)}  → "
              f"11:{h[11]} 12:{h[12]} 13:{h[13]} 14:{h[14]} "
              f"| R$ {premio:>8,.2f} | ROI {roi:>5.1f}%")


if __name__ == "__main__":
    main()
