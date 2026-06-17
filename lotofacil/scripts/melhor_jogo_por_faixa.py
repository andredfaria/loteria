"""Find the best 15-number combination for each exact hit tier (11–15 acertos)."""

import heapq
import itertools
import sys
import time
from collections import Counter
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC_DIR))

from lotofacil.infra.config import DADOS_DIR
from lotofacil.infra.dados.leitor import load_draws


def main():
    print("Carregando sorteios...")
    draws = load_draws(DADOS_DIR)
    total = len(draws)
    print(f"Total: {total} sorteios\n")

    # ── frequência individual ──
    counter = Counter()
    for d in draws:
        counter.update(d.dezenas)
    freq = [0] * 26
    for n, c in counter.most_common():
        freq[n] = c
    sorted_freq = counter.most_common()

    print(f"{'FREQUÊNCIA DOS NÚMEROS (1–25)':^62}")
    print(f"{'='*62}")
    print(f"{'#':>4} | {'Nº':>4} | {'Frequência':>12} | {'%':>8}")
    print(f"{'-'*4}-+-{'-'*4}-+-{'-'*12}-+-{'-'*8}")
    for i, (n, c) in enumerate(sorted_freq, 1):
        mark = " ◄" if i <= 15 else ""
        print(f"{i:>4} | {n:>4} | {c:>12} | {c/total*100:>7.2f}%{mark}")

    # ── top 1000 combos por score total ──
    print(f"\nGerando top 1000 combinações candidatas...")
    t0 = time.time()

    def sum_freq(combo):
        return sum(freq[n] for n in combo)

    top1000 = heapq.nlargest(
        1000,
        itertools.combinations(range(1, 26), 15),
        key=sum_freq,
    )
    print(f"  {len(top1000)} combinações em {time.time()-t0:.1f}s")

    # ── avaliar cada combo contra todos os sorteios ──
    print(f"Avaliando contra {total} sorteios...")
    t0 = time.time()
    resultados = []
    for combo in top1000:
        s = set(combo)
        hits = Counter()
        for d in draws:
            k = len(s & set(d.dezenas))
            if k >= 11:
                hits[k] += 1
        # total 11+ ponderado pelo prêmio
        premio = (hits[11] * 7.0 + hits[12] * 14.0 + hits[13] * 35.0 +
                  hits[14] * 2000.0 + hits[15] * 1500000.0)
        resultados.append((combo, hits, premio))
    print(f"  Avaliação concluída em {time.time()-t0:.1f}s\n")

    # ── exibir top 3 por faixa ──
    faixas = [11, 12, 13, 14, 15]
    melhores = {}
    for k in faixas:
        top3 = sorted(resultados, key=lambda x: x[1][k], reverse=True)[:3]
        melhores[k] = top3

    for k in faixas:
        print(f"{'='*90}")
        label = f"  TOP 3 — EXATAMENTE {k} ACERTOS"
        if k == 15:
            label += " (MEGA-SENA DA LOTOFÁCIL)"
        print(f"{label:^90}")
        print(f"{'='*90}")

        for rank, (combo, hits, premio) in enumerate(melhores[k], 1):
            total_11_mais = sum(hits[f] for f in faixas)
            custo = total * 3.50
            roi = (premio / custo) * 100 if custo else 0

            header = "  🏆 CAMPEÃO" if rank == 1 else f"  #{rank} LUGAR"
            print(f"\n  {header}")
            print(f"  {'─'*80}")
            print(f"  Números: {sorted(combo)}")
            print(f"  {k} acertos: {hits[k]}x em {total} sorteios ({hits[k]/total*100:.2f}%)")
            print(f"  Faixas:")
            for f in faixas:
                bar = "■" * min(hits[f], 30) + " " * max(0, 30 - min(hits[f], 30))
                print(f"    {f:2d} acertos: {hits[f]:>4}x  {bar}")
            print(f"  Prêmio total (R$): {premio:>12,.2f}")
            print(f"  Custo total (R$):  {custo:>12,.2f}")
            print(f"  ROI: {roi:>6.1f}%")

    # ── best overall por ROI ponderado ──
    print(f"\n{'='*90}")
    print(f"{'🏆  MELHOR CUSTO-BENEFÍCIO (MAIOR PREMIAÇÃO TOTAL)':^90}")
    print(f"{'='*90}")
    melhor = max(resultados, key=lambda x: x[2])
    combo, hits, premio = melhor
    custo = total * 3.50
    roi = (premio / custo) * 100
    print(f"\n  Números: {sorted(combo)}")
    print(f"  {'─'*60}")
    for k in faixas:
        print(f"    {k:2d} acertos: {hits[k]:>4}x")
    print(f"  Prêmio total: R$ {premio:>12,.2f}")
    print(f"  Custo total:  R$ {custo:>12,.2f}")
    print(f"  ROI: {roi:.1f}%")
    print(f"  Lucro: {'R$ ' + f'{premio - custo:,.2f}' if premio > custo else 'PREJUÍZO'}")

    # ── comparação com os 15 mais frequentes (benchmark) ──
    benchmark_combo = tuple(n for n, _ in sorted_freq[:15])
    print(f"\n{'='*90}")
    print(f"{'📊  BENCHMARK — 15 NÚMEROS MAIS FREQUENTES':^90}")
    print(f"{'='*90}")
    s_bench = set(benchmark_combo)
    bench_hits = Counter()
    for d in draws:
        k = len(s_bench & set(d.dezenas))
        if k >= 11:
            bench_hits[k] += 1
    bench_premio = sum(bench_hits[f] * [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 7, 14, 35, 2000, 1500000][f] for f in faixas)
    bench_custo = total * 3.50
    bench_roi = (bench_premio / bench_custo) * 100
    print(f"\n  Números: {sorted(benchmark_combo)}")
    for k in faixas:
        print(f"    {k:2d} acertos: {bench_hits[k]:>4}x")
    print(f"  Prêmio total: R$ {bench_premio:>12,.2f}")
    print(f"  ROI: {bench_roi:.1f}%")

    melhor_nome = "Os 15 mais frequentes" if melhor[0] == benchmark_combo else "O campeão acima"
    print(f"\n  → Melhor que o benchmark? {'SIM' if premio > bench_premio else 'NÃO'}")


if __name__ == "__main__":
    main()
