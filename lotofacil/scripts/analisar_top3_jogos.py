"""Find top 3 combinations of 15 numbers with highest total matches across all Lotofácil draws."""

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
    print(f"Total de sorteios carregados: {len(draws)}")

    print("Calculando frequência dos números...")
    counter = Counter()
    for draw in draws:
        counter.update(draw.dezenas)

    sorted_freq = counter.most_common()
    freq_list = [0] * 26
    for num, count in sorted_freq:
        freq_list[num] = count

    total_draws = len(draws)
    print(f"\n{'='*62}")
    print(f"{'FREQUÊNCIA DOS NÚMEROS (1–25)':^62}")
    print(f"{'='*62}")
    print(f"{'#':>4} | {'Nº':>4} | {'Frequência':>12} | {'%':>8}")
    print(f"{'-'*4}-+-{'-'*4}-+-{'-'*12}-+-{'-'*8}")
    for i, (num, count) in enumerate(sorted_freq, 1):
        pct = count / total_draws * 100
        mark = " ◄" if i <= 15 else ""
        print(f"{i:>4} | {num:>4} | {count:>12} | {pct:>7.2f}%{mark}")

    print(f"\nBuscando top 3 combinações entre 3.268.760 possíveis...")
    sys.stdout.flush()
    t0 = time.time()

    def sum_freq(combo):
        return sum(freq_list[n] for n in combo)

    all_nums = list(range(1, 26))
    top3 = heapq.nlargest(3, itertools.combinations(all_nums, 15), key=sum_freq)

    elapsed = time.time() - t0
    print(f"Busca concluída em {elapsed:.1f}s")

    print(f"\n{'='*90}")
    print(f"{'TOP 3 COMBINAÇÕES QUE MAIS ACERTARAM EM TODA HISTÓRIA':^90}")
    print(f"{'='*90}")

    for rank, combo in enumerate(top3, 1):
        score = sum_freq(combo)
        sorted_combo = sorted(combo)
        exact_matches = sum(1 for d in draws if set(d.dezenas) == set(combo))
        avg = score / total_draws

        header = "  🏆 CAMPEÃO" if rank == 1 else f"  #{rank} LUGAR"
        print(f"\n  {header}")
        print(f"  {'─'*70}")
        print(f"  Números: {sorted_combo}")
        print(f"  Pontuação total: {score:,} acertos em {total_draws} sorteios")
        print(f"  Média: {avg:.2f} acertos por sorteio")
        print(f"  Vezes sorteado exatamente: {exact_matches}")
        if rank > 1:
            champ_score = sum_freq(top3[0])
            diff = champ_score - score
            print(f"  Diferença para o campeão: {diff} acertos")

    champ = top3[0]
    champ_combo = sorted(champ)
    champ_score = sum_freq(champ)
    print(f"\n{'='*90}")
    print(f"{'🏆  JOGO CAMPEÃO — OS 15 NÚMEROS QUE MAIS ACERTAM':^90}")
    print(f"{'='*90}")
    print(f"\n  {champ_combo}")
    print(f"\n  Pontuação total: {champ_score:,} acertos em {total_draws} sorteios")
    print(f"  Média: {champ_score/total_draws:.2f} acertos por sorteio")
    print(f"\n  Detalhamento por número:")
    print(f"  {'Nº':>4} | {'Frequência':>12} | {'%':>8}")
    print(f"  {'-'*4}-+-{'-'*12}-+-{'-'*8}")
    for n in champ_combo:
        count = freq_list[n]
        pct = count / total_draws * 100
        print(f"  {n:>4} | {count:>12} | {pct:>7.2f}%")


if __name__ == "__main__":
    main()
