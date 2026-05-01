"""
Backtest walk-forward: testa diferentes pesos ML vs padrões nos últimos N concursos.
Para cada concurso alvo, usa apenas dados anteriores a ele para gerar o jogo.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from geracao.gerador_jogos_lotofacil import (
    carregar_dados_historicos,
    calcular_frequencia_numeros,
    calcular_distribuicao_pares_impares,
    calcular_distribuicao_somas,
    analisar_consecutivos,
    obter_probabilidades_ml,
    obter_probabilidades_estatistica,
    mesclar_probabilidades,
    gerar_jogo_hibrido,
)

import numpy as np

JANELA_ML = 120
N_CONCURSOS = 30


def calcular_estatisticas(concursos):
    return {
        "frequencia": calcular_frequencia_numeros(concursos),
        "pares_impares": calcular_distribuicao_pares_impares(concursos),
        "somas": calcular_distribuicao_somas(concursos),
        "consecutivos": analisar_consecutivos(concursos),
    }


def gerar_jogo_hibrido_silencioso(concursos_historico, peso_ml):
    """Gera jogo sem prints."""
    import io, contextlib
    ultimo = concursos_historico[-1]["dezenas"]
    freq = calcular_frequencia_numeros(concursos_historico)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        probs_ml = obter_probabilidades_ml(concursos_historico, janela=JANELA_ML)
        probs_estat = obter_probabilidades_estatistica(concursos_historico, ultimo)
    probs = mesclar_probabilidades(probs_ml, probs_estat, peso_ml=peso_ml)
    return gerar_jogo_hibrido(probs, ultimo, freq, concursos_historico)


def backtest(todos_concursos, peso_ml, n=N_CONCURSOS):
    alvos = todos_concursos[-n:]
    acertos = []
    for c in alvos:
        num_alvo = c["concurso"]
        historico = [x for x in todos_concursos if x["concurso"] < num_alvo]
        if len(historico) < 20:
            continue
        jogo = gerar_jogo_hibrido_silencioso(historico, peso_ml)
        resultado = set(c["dezenas"])
        pontos = len(set(jogo) & resultado)
        acertos.append((num_alvo, jogo, sorted(c["dezenas"]), pontos))
    return acertos


def main():
    print("Carregando dados históricos...")
    todos = carregar_dados_historicos()
    if not todos:
        print("Erro: sem dados.")
        return

    print(f"Total: {len(todos)} concursos. Testando últimos {N_CONCURSOS}.\n")

    pesos = [round(x * 0.1, 1) for x in range(0, 11)]  # 0.0 a 1.0
    resultados = {}

    for peso in pesos:
        print(f"  Testando peso_ml={peso:.1f} ({peso*100:.0f}% ML + {100-peso*100:.0f}% padrões)...", end=" ", flush=True)
        acertos = backtest(todos, peso_ml=peso)
        pontos = [a[3] for a in acertos]
        media = np.mean(pontos)
        maximo = max(pontos)
        minimo = min(pontos)
        dist = {p: pontos.count(p) for p in range(11, 16)}
        resultados[peso] = {"acertos": acertos, "media": media, "max": maximo, "min": minimo, "dist": dist}
        print(f"média={media:.2f}  min={minimo}  max={maximo}  dist={dist}")

    # Ranking
    print("\n" + "=" * 70)
    print("RANKING — por média de acertos (maior = melhor)")
    print("=" * 70)
    ranking = sorted(resultados.items(), key=lambda x: x[1]["media"], reverse=True)
    print(f"{'Peso ML':>8} {'Padrões':>8} {'Média':>7} {'Min':>4} {'Max':>4}  Distribuição (11-15 pts)")
    print("-" * 70)
    for peso, r in ranking:
        dist_str = "  ".join(f"{p}pts:{r['dist'].get(p,0)}x" for p in range(11, 16))
        print(f"  {peso*100:>5.0f}%   {100-peso*100:>5.0f}%   {r['media']:>6.2f}   {r['min']:>3}   {r['max']:>3}   {dist_str}")

    melhor_peso = ranking[0][0]
    print(f"\n✅ Melhor peso: {melhor_peso*100:.0f}% ML + {100-melhor_peso*100:.0f}% padrões (média {ranking[0][1]['media']:.2f} acertos)")

    # Detalhes do melhor
    print(f"\nDetalhe dos {N_CONCURSOS} concursos com peso_ml={melhor_peso:.1f}:")
    print(f"{'Concurso':>10}  {'Acertos':>7}  Jogo Gerado")
    print("-" * 65)
    for num, jogo, resultado, pts in resultados[melhor_peso]["acertos"]:
        acertos_str = ", ".join(str(n) for n in sorted(set(jogo) & set(resultado)))
        print(f"  {num:>8}     {pts:>2}pts   {jogo}   ✓{acertos_str}")

    return melhor_peso, ranking


if __name__ == "__main__":
    main()
