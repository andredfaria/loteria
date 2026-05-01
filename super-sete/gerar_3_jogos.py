#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gera 3 jogos para o próximo concurso da Super Sete usando estratégias diferentes."""

from analise_estatistica import (
    carregar_dados_historicos,
    calcular_frequencias,
    calcular_atrasos,
    calcular_desvio_uniforme,
    calcular_entropia,
    calcular_tendencia_temporal,
    calcular_correlacao_temporal,
    calcular_scores_todos_digitos,
    NUM_COLUNAS,
)

ARQUIVO = "dados/numeros_sorteados.json"

ESTRATEGIAS = [
    {
        "nome": "Jogo 1 - Equilibrado",
        "descricao": "Balanço entre frequência, atraso e tendência",
        "pesos": {"frequencia": 0.25, "atraso": 0.30, "tendencia": 0.20, "entropia": 0.10, "exploracao": 0.15},
    },
    {
        "nome": "Jogo 2 - Atraso Dominante",
        "descricao": "Prioriza dígitos que estão atrasados (não saem há mais tempo)",
        "pesos": {"frequencia": 0.10, "atraso": 0.55, "tendencia": 0.15, "entropia": 0.05, "exploracao": 0.15},
    },
    {
        "nome": "Jogo 3 - Tendência Recente",
        "descricao": "Prioriza dígitos em alta nos últimos 50 concursos",
        "pesos": {"frequencia": 0.15, "atraso": 0.20, "tendencia": 0.45, "entropia": 0.05, "exploracao": 0.15},
    },
]


def selecionar_top_digito(scores_col):
    return max(scores_col.items(), key=lambda x: x[1])[0]


def main():
    print("Carregando dados históricos...")
    dados = carregar_dados_historicos(ARQUIVO)
    ultimo = dados[-1]
    print(f"Concursos carregados: {len(dados)} (último: #{ultimo.get('concurso')} em {ultimo.get('data')})")

    print("Calculando métricas...\n")
    frequencias = calcular_frequencias(dados)
    atrasos = calcular_atrasos(dados)
    desvios = calcular_desvio_uniforme(frequencias["relativas"])
    entropia = calcular_entropia(frequencias["relativas"])
    tendencia = calcular_tendencia_temporal(dados)
    correlacao = calcular_correlacao_temporal(dados)

    metricas = {
        "frequencias": frequencias,
        "atrasos": atrasos,
        "desvios": desvios,
        "entropia": entropia,
        "tendencia": tendencia,
        "correlacao": correlacao,
    }

    print("=" * 60)
    print("JOGOS RECOMENDADOS - SUPER SETE - CONCURSO 833")
    print("=" * 60)

    for est in ESTRATEGIAS:
        pesos = est["pesos"]
        soma = sum(pesos.values())
        pesos_norm = {k: v / soma for k, v in pesos.items()}

        scores = calcular_scores_todos_digitos(metricas, pesos_norm)

        jogo = [selecionar_top_digito(scores.get(col, {})) for col in range(1, NUM_COLUNAS + 1)]

        print(f"\n{est['nome']}")
        print(f"  Estrategia: {est['descricao']}")
        print(f"  Numeros:    {' | '.join(str(d) for d in jogo)}")
        print(f"              Col 1  Col 2  Col 3  Col 4  Col 5  Col 6  Col 7")

        # Mostrar score de cada digito escolhido
        score_info = []
        for col in range(1, NUM_COLUNAS + 1):
            d = jogo[col - 1]
            s = scores.get(col, {}).get(d, 0.0)
            score_info.append(f"  Col {col}: digito {d} (score {s:.3f})")
        print("  " + " | ".join(score_info))

    print("\n" + "=" * 60)
    print("AVISO: Sorteios de loteria sao aleatórios. Esta análise é")
    print("estatística exploratória, não previsão. Jogue com responsabilidade.")
    print("=" * 60)


if __name__ == "__main__":
    main()
