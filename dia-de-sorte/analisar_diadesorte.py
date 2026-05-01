#!/usr/bin/env python3
"""
Analisador Dia de Sorte — análise estatística e sugestão de jogos.

Uso:
  python analisar_diadesorte.py --dados dados/ --estrategia mista --jogos 5
  python analisar_diadesorte.py --dados dados/ --estrategia equilibrada --sem-metricas
  python analisar_diadesorte.py --dados dados/ --seed 42
"""
import csv
import json
import os
import random
from collections import Counter

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

TODOS_NUMEROS = list(range(1, 32))           # 1..31
TODOS_MESES = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]
NUM_BAIXO_MAX = 15    # 1..15 = baixos, 16..31 = altos
TOTAL_DEZENAS = 7

CONFIG_PADRAO = {
    "estrategia":     "mista",   # frequentes | atrasados | mista | equilibrada
    "min_frequentes": 2,
    "max_frequentes": 4,
    "min_atrasados":  1,
    "max_atrasados":  3,
    "min_pares":      2,
    "max_pares":      5,
    "min_baixos":     2,
    "max_baixos":     5,
    "n_jogos":        1,
}


# ---------------------------------------------------------------------------
# Seção 1 — Carregamento de dados
# ---------------------------------------------------------------------------

def carregar_dados(caminho: str) -> list[dict]:
    """
    Carrega histórico de concursos.
    Aceita:
      - diretório com arquivos diadesorte_N.json
      - arquivo .json com lista de concursos
      - arquivo .csv com colunas: concurso,data,n1..n7,mes_sorte
    Retorna lista de concursos normalizados, ordenados por número.
    """
    if os.path.isdir(caminho):
        return _carregar_diretorio(caminho)
    if caminho.endswith(".json"):
        return _carregar_json_arquivo(caminho)
    if caminho.endswith(".csv"):
        return _carregar_csv(caminho)
    raise ValueError(
        f"Formato não suportado: {caminho!r}. Use diretório, .json ou .csv."
    )


def _carregar_diretorio(caminho: str) -> list[dict]:
    historico = []
    for nome in sorted(os.listdir(caminho)):
        if not nome.endswith(".json"):
            continue
        filepath = os.path.join(caminho, nome)
        with open(filepath, encoding="utf-8") as f:
            raw = json.load(f)
        historico.append(_normalizar_json(raw))
    historico.sort(key=lambda x: x["concurso"])
    return historico


def _carregar_json_arquivo(caminho: str) -> list[dict]:
    with open(caminho, encoding="utf-8") as f:
        raw = json.load(f)
    registros = raw if isinstance(raw, list) else [raw]
    historico = [_normalizar_json(r) for r in registros]
    historico.sort(key=lambda x: x["concurso"])
    return historico


def _carregar_csv(caminho: str) -> list[dict]:
    historico = []
    with open(caminho, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            numeros = sorted(int(row[f"n{i}"]) for i in range(1, 8))
            historico.append({
                "concurso":  int(row["concurso"]),
                "data":      row.get("data", ""),
                "numeros":   numeros,
                "mes_sorte": row.get("mes_sorte", ""),
            })
    historico.sort(key=lambda x: x["concurso"])
    return historico


def _normalizar_json(raw: dict) -> dict:
    return {
        "concurso":  int(raw["concurso"]),
        "data":      raw.get("data", ""),
        "numeros":   sorted(int(d) for d in raw["dezenas"]),
        "mes_sorte": raw.get("mesSorte", raw.get("mes_sorte", "")),
    }


# ---------------------------------------------------------------------------
# Seção 2 — Cálculo de métricas
# ---------------------------------------------------------------------------

def calc_frequencia(historico: list[dict]) -> dict[int, int]:
    """Conta quantas vezes cada número (1-31) apareceu no histórico."""
    freq = {n: 0 for n in TODOS_NUMEROS}
    for concurso in historico:
        for n in concurso["numeros"]:
            freq[n] += 1
    return freq


def calc_atraso(historico: list[dict]) -> dict[int, int]:
    """
    Retorna, para cada número, quantos concursos se passaram desde a última aparição.
    Números que nunca apareceram recebem atraso = total de concursos.
    """
    ultimo_visto = {n: 0 for n in TODOS_NUMEROS}
    for concurso in historico:
        for n in concurso["numeros"]:
            ultimo_visto[n] = concurso["concurso"]
    ultimo_id = historico[-1]["concurso"]
    return {n: ultimo_id - ultimo_visto[n] for n in TODOS_NUMEROS}


def calc_distribuicao_paridade(historico: list[dict]) -> dict:
    """Calcula média histórica de pares e ímpares por concurso."""
    pares_por_jogo = [
        sum(1 for n in c["numeros"] if n % 2 == 0)
        for c in historico
    ]
    media_pares = sum(pares_por_jogo) / len(historico)
    return {
        "media_pares":   media_pares,
        "media_impares": TOTAL_DEZENAS - media_pares,
    }


def calc_distribuicao_faixa(historico: list[dict]) -> dict:
    """Calcula média histórica de números baixos (1-15) e altos (16-31) por concurso."""
    baixos_por_jogo = [
        sum(1 for n in c["numeros"] if n <= NUM_BAIXO_MAX)
        for c in historico
    ]
    media_baixos = sum(baixos_por_jogo) / len(historico)
    return {
        "media_baixos": media_baixos,
        "media_altos":  TOTAL_DEZENAS - media_baixos,
    }


def calc_frequencia_mes(historico: list[dict]) -> dict[str, int]:
    """Conta quantas vezes cada mês da sorte foi sorteado."""
    freq = {m: 0 for m in TODOS_MESES}
    for c in historico:
        mes = c.get("mes_sorte", "")
        if mes in freq:
            freq[mes] += 1
    return freq


def calcular_metricas(historico: list[dict]) -> dict:
    """Agrega todas as métricas em um único dicionário."""
    return {
        "frequencia":      calc_frequencia(historico),
        "atraso":          calc_atraso(historico),
        "paridade":        calc_distribuicao_paridade(historico),
        "faixa":           calc_distribuicao_faixa(historico),
        "frequencia_mes":  calc_frequencia_mes(historico),
        "total_concursos": len(historico),
    }


# ---------------------------------------------------------------------------
# Seção 3 — Estratégias de seleção
# ---------------------------------------------------------------------------

def _rankear(valores: dict, reverso: bool = True) -> dict[int, int]:
    """Retorna {número: rank} onde rank=1 é o melhor."""
    ordenado = sorted(TODOS_NUMEROS, key=lambda n: valores[n], reverse=reverso)
    return {n: i + 1 for i, n in enumerate(ordenado)}


def _normalizar_pesos(valores: dict) -> list[float]:
    """Transforma valores em pesos normalizados (soma=1) na ordem de TODOS_NUMEROS."""
    vals = [max(valores.get(n, 0.001), 0.001) for n in TODOS_NUMEROS]
    total = sum(vals)
    return [v / total for v in vals]


def _normalizar_pesos_lista(pool: list[int], valores: dict) -> list[float]:
    """Pesos normalizados para uma lista arbitrária de números."""
    vals = [max(valores.get(n, 0.001), 0.001) for n in pool]
    total = sum(vals)
    return [v / total for v in vals]


def _amostrar_sem_repeticao(pesos: list[float], k: int) -> list[int]:
    """Seleciona k números de TODOS_NUMEROS sem repetição, usando pesos proporcionais."""
    pool = list(TODOS_NUMEROS)
    pesos_mut = list(pesos)
    escolhidos = []
    for _ in range(k):
        idx = random.choices(range(len(pool)), weights=pesos_mut)[0]
        escolhidos.append(pool[idx])
        pool.pop(idx)
        pesos_mut.pop(idx)
    return escolhidos


def _selecionar_frequentes(metricas: dict, n: int = TOTAL_DEZENAS) -> tuple[list[int], dict]:
    freq = metricas["frequencia"]
    rank = _rankear(freq, reverso=True)
    pesos = _normalizar_pesos({num: 1 / rank[num] for num in TODOS_NUMEROS})
    escolhidos = _amostrar_sem_repeticao(pesos, n)
    razoes = {
        num: f"Frequente: {freq[num]}x no histórico (rank #{rank[num]})"
        for num in escolhidos
    }
    return escolhidos, razoes


def _selecionar_atrasados(metricas: dict, n: int = TOTAL_DEZENAS) -> tuple[list[int], dict]:
    atraso = metricas["atraso"]
    rank = _rankear(atraso, reverso=True)
    pesos = _normalizar_pesos({num: 1 / rank[num] for num in TODOS_NUMEROS})
    escolhidos = _amostrar_sem_repeticao(pesos, n)
    razoes = {
        num: f"Atrasado: {atraso[num]} concursos sem aparecer (rank #{rank[num]})"
        for num in escolhidos
    }
    return escolhidos, razoes


def _selecionar_mista(metricas: dict, config: dict) -> tuple[list[int], dict]:
    """
    Mistura números frequentes e atrasados conforme limites do config.
    Preenche o restante com seleção ponderada pelo score combinado.
    """
    freq   = metricas["frequencia"]
    atraso = metricas["atraso"]
    rank_f = _rankear(freq,   reverso=True)
    rank_a = _rankear(atraso, reverso=True)

    n_freq   = random.randint(config["min_frequentes"], config["max_frequentes"])
    n_atraso = random.randint(config["min_atrasados"],  config["max_atrasados"])
    n_freq   = min(n_freq,   TOTAL_DEZENAS)
    n_atraso = min(n_atraso, TOTAL_DEZENAS - n_freq)
    n_resto  = TOTAL_DEZENAS - n_freq - n_atraso

    top_freq   = sorted(TODOS_NUMEROS, key=lambda n: rank_f[n])
    top_atraso = sorted(TODOS_NUMEROS, key=lambda n: rank_a[n])

    escolhidos_f = []
    for n in top_freq:
        if len(escolhidos_f) == n_freq:
            break
        escolhidos_f.append(n)

    usados = set(escolhidos_f)
    escolhidos_a = []
    for n in top_atraso:
        if len(escolhidos_a) == n_atraso:
            break
        if n not in usados:
            escolhidos_a.append(n)
            usados.add(n)

    disponiveis = [n for n in TODOS_NUMEROS if n not in usados]
    score_comb  = {n: 1 / rank_f[n] + 1 / rank_a[n] for n in disponiveis}
    pesos_resto = _normalizar_pesos_lista(disponiveis, score_comb)

    pool = list(disponiveis)
    pw   = list(pesos_resto)
    escolhidos_r = []
    for _ in range(n_resto):
        if not pool:
            break
        idx = random.choices(range(len(pool)), weights=pw)[0]
        escolhidos_r.append(pool[idx])
        pool.pop(idx)
        pw.pop(idx)

    razoes = {}
    for n in escolhidos_f:
        razoes[n] = f"Frequente: {freq[n]}x (rank #{rank_f[n]})"
    for n in escolhidos_a:
        razoes[n] = f"Atrasado: {atraso[n]} concursos (rank #{rank_a[n]})"
    for n in escolhidos_r:
        razoes[n] = f"Complementar: freq={freq[n]}, atraso={atraso[n]}"

    return escolhidos_f + escolhidos_a + escolhidos_r, razoes


def _selecionar_equilibrada(metricas: dict, config: dict) -> tuple[list[int], dict]:
    """
    Seleciona com restrições de paridade e faixa usando rejection sampling.
    Score por número = média normalizada de frequência e atraso.
    """
    freq   = metricas["frequencia"]
    atraso = metricas["atraso"]
    rank_f = _rankear(freq,   reverso=True)
    rank_a = _rankear(atraso, reverso=True)

    pesos_base = _normalizar_pesos({
        n: (1 / rank_f[n] + 1 / rank_a[n]) for n in TODOS_NUMEROS
    })

    min_pares  = config.get("min_pares",  2)
    max_pares  = config.get("max_pares",  5)
    min_baixos = config.get("min_baixos", 2)
    max_baixos = config.get("max_baixos", 5)

    for _ in range(2000):
        candidatos = _amostrar_sem_repeticao(pesos_base, TOTAL_DEZENAS)
        pares  = sum(1 for n in candidatos if n % 2 == 0)
        baixos = sum(1 for n in candidatos if n <= NUM_BAIXO_MAX)
        if min_pares <= pares <= max_pares and min_baixos <= baixos <= max_baixos:
            razoes = {
                n: (
                    f"Equilibrado: freq={freq[n]} (#{rank_f[n]}), "
                    f"atraso={atraso[n]} (#{rank_a[n]}), "
                    f"{'par' if n % 2 == 0 else 'ímpar'}, "
                    f"{'baixo' if n <= NUM_BAIXO_MAX else 'alto'}"
                )
                for n in candidatos
            }
            return candidatos, razoes

    # Fallback: top-7 por score combinado
    top7 = sorted(
        TODOS_NUMEROS,
        key=lambda n: (1 / rank_f[n] + 1 / rank_a[n]),
        reverse=True
    )[:TOTAL_DEZENAS]
    razoes = {
        n: f"Fallback equilibrado: freq={freq[n]}, atraso={atraso[n]}"
        for n in top7
    }
    return top7, razoes


def _selecionar_mes(metricas: dict) -> str:
    """Escolhe mês da sorte com probabilidade proporcional à frequência histórica."""
    freq_mes = metricas["frequencia_mes"]
    total    = sum(freq_mes.values())
    if total == 0:
        return random.choice(TODOS_MESES)
    pesos = [freq_mes[m] / total for m in TODOS_MESES]
    return random.choices(TODOS_MESES, weights=pesos)[0]


# ---------------------------------------------------------------------------
# Seção 4 — Gerador de jogo + pontuação
# ---------------------------------------------------------------------------

def _calcular_score(numeros: list[int], mes_sorte: str, metricas: dict, config: dict) -> float:
    """
    Score 0-100 para o jogo:
      30% equilíbrio de paridade  (ideal: 3-4 pares)
      30% equilíbrio de faixa     (ideal: 3-4 baixos)
      20% rank médio de frequência
      20% rank médio de atraso
    """
    freq   = metricas["frequencia"]
    atraso = metricas["atraso"]
    rank_f = _rankear(freq,   reverso=True)
    rank_a = _rankear(atraso, reverso=True)

    pares  = sum(1 for n in numeros if n % 2 == 0)
    baixos = sum(1 for n in numeros if n <= NUM_BAIXO_MAX)

    score_paridade = max(0.0, 100 - abs(pares  - 3.5) * 25)
    score_faixa    = max(0.0, 100 - abs(baixos - 3.5) * 25)
    score_freq     = sum((31 - rank_f[n]) / 30 * 100 for n in numeros) / len(numeros)
    score_atraso   = sum((31 - rank_a[n]) / 30 * 100 for n in numeros) / len(numeros)

    score = (
        score_paridade * 0.30 +
        score_faixa    * 0.30 +
        score_freq     * 0.20 +
        score_atraso   * 0.20
    )
    return round(min(score, 100.0), 2)


def gerar_jogo(metricas: dict, config: dict) -> dict:
    """
    Gera um jogo com 7 números e 1 mês da sorte conforme estratégia e config.

    Retorna:
      numeros      — lista de 7 ints ordenados (1-31)
      mes_sorte    — string do mês escolhido
      razoes       — dict {numero: motivo_da_escolha}
      score        — float 0-100 (qualidade pela estratégia)
      estrategia   — nome da estratégia usada
      metricas_jogo — pares, ímpares, baixos, altos
    """
    estrategia = config.get("estrategia", "mista")

    if estrategia == "frequentes":
        numeros, razoes = _selecionar_frequentes(metricas)
    elif estrategia == "atrasados":
        numeros, razoes = _selecionar_atrasados(metricas)
    elif estrategia == "mista":
        numeros, razoes = _selecionar_mista(metricas, config)
    elif estrategia == "equilibrada":
        numeros, razoes = _selecionar_equilibrada(metricas, config)
    else:
        raise ValueError(f"Estratégia desconhecida: {estrategia!r}")

    numeros   = sorted(numeros)
    mes_sorte = _selecionar_mes(metricas)
    score     = _calcular_score(numeros, mes_sorte, metricas, config)

    return {
        "numeros":   numeros,
        "mes_sorte": mes_sorte,
        "razoes":    razoes,
        "score":     score,
        "estrategia": estrategia,
        "metricas_jogo": {
            "pares":   sum(1 for n in numeros if n % 2 == 0),
            "impares": sum(1 for n in numeros if n % 2 != 0),
            "baixos":  sum(1 for n in numeros if n <= NUM_BAIXO_MAX),
            "altos":   sum(1 for n in numeros if n > NUM_BAIXO_MAX),
        },
    }


# ---------------------------------------------------------------------------
# Seção 5 — Ranqueador de múltiplos jogos
# ---------------------------------------------------------------------------

def gerar_e_ranquear(metricas: dict, config: dict, n_jogos: int = 10) -> list[dict]:
    """
    Gera n_jogos candidatos e os ordena por score decrescente.
    Adiciona campo 'posicao' (1-based) a cada jogo.
    """
    jogos = [gerar_jogo(metricas, config) for _ in range(n_jogos)]
    jogos.sort(key=lambda j: j["score"], reverse=True)
    for i, jogo in enumerate(jogos, start=1):
        jogo["posicao"] = i
    return jogos


# ---------------------------------------------------------------------------
# Seção 6 — Funções de exibição
# ---------------------------------------------------------------------------

def exibir_metricas(metricas: dict) -> None:
    """Imprime resumo das métricas no terminal."""
    total    = metricas["total_concursos"]
    freq     = metricas["frequencia"]
    atraso   = metricas["atraso"]
    par      = metricas["paridade"]
    faixa    = metricas["faixa"]
    freq_mes = metricas["frequencia_mes"]

    print("\n" + "=" * 62)
    print(f"  METRICAS — Dia de Sorte  ({total} concursos analisados)")
    print("=" * 62)

    print("\n  [Frequencia — Top 10 mais sorteados]")
    top10_freq = sorted(TODOS_NUMEROS, key=lambda n: freq[n], reverse=True)[:10]
    for n in top10_freq:
        barra = "█" * int(freq[n] / max(freq.values()) * 30)
        print(f"    {n:02d}: {freq[n]:4d}x  {barra}")

    print("\n  [Atraso — Top 10 mais ausentes]")
    top10_atraso = sorted(TODOS_NUMEROS, key=lambda n: atraso[n], reverse=True)[:10]
    for n in top10_atraso:
        print(f"    {n:02d}: {atraso[n]:4d} concursos sem aparecer")

    print(f"\n  [Paridade historica]")
    print(f"    Media de pares por jogo:   {par['media_pares']:.2f}")
    print(f"    Media de impares por jogo: {par['media_impares']:.2f}")

    print(f"\n  [Faixa historica]")
    print(f"    Media de baixos (1-15):  {faixa['media_baixos']:.2f}")
    print(f"    Media de altos  (16-31): {faixa['media_altos']:.2f}")

    print(f"\n  [Mes da Sorte — frequencia]")
    max_mes = max(freq_mes.values()) or 1
    for mes in TODOS_MESES:
        pct   = freq_mes[mes] / total * 100 if total else 0
        barra = "█" * int(freq_mes[mes] / max_mes * 20)
        print(f"    {mes:<11}: {freq_mes[mes]:4d}x ({pct:5.1f}%)  {barra}")

    print()


def exibir_jogo(jogo: dict, posicao: int | None = None) -> None:
    """Imprime jogo sugerido com razões e métricas."""
    titulo = "  JOGO SUGERIDO" if posicao is None else f"  JOGO #{posicao}"
    print("\n" + "=" * 62)
    print(f"{titulo}  [estrategia: {jogo['estrategia']}]  score: {jogo['score']:.1f}/100")
    print("=" * 62)

    print(f"\n  Numeros:     {' '.join(f'{n:02d}' for n in jogo['numeros'])}")
    print(f"  Mes da Sorte: {jogo['mes_sorte']}")

    mj = jogo["metricas_jogo"]
    print(
        f"\n  Composicao: {mj['pares']} par(es) / {mj['impares']} impar(es)"
        f"  |  {mj['baixos']} baixo(s) / {mj['altos']} alto(s)"
    )

    print("\n  Razao de cada numero:")
    for n in jogo["numeros"]:
        razao = jogo["razoes"].get(n, "—")
        print(f"    {n:02d} → {razao}")

    print()


def exibir_ranking(jogos: list[dict]) -> None:
    """Imprime lista ranqueada de jogos."""
    print("\n" + "=" * 62)
    print(f"  RANKING DE {len(jogos)} JOGOS GERADOS")
    print("=" * 62)
    for jogo in jogos:
        nums = " ".join(f"{n:02d}" for n in jogo["numeros"])
        print(
            f"  #{jogo['posicao']:2d}  score={jogo['score']:5.1f}"
            f"  [{nums}]  mes={jogo['mes_sorte']}"
        )
    print()


# ---------------------------------------------------------------------------
# Seção 7 — CLI
# ---------------------------------------------------------------------------

def _parse_args():
    import argparse

    p = argparse.ArgumentParser(
        description=(
            "Analisador Dia de Sorte — sugere jogos com base em estatísticas históricas.\n\n"
            "Exemplos:\n"
            "  python analisar_diadesorte.py --dados dados/\n"
            "  python analisar_diadesorte.py --dados dados/ --estrategia equilibrada --jogos 5\n"
            "  python analisar_diadesorte.py --dados dados/ --seed 42 --sem-metricas\n"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    p.add_argument(
        "--dados", default="dados",
        help="Diretório com JSONs, arquivo .json ou .csv (padrão: dados/)",
    )
    p.add_argument(
        "--estrategia", default="mista",
        choices=["frequentes", "atrasados", "mista", "equilibrada"],
        help=(
            "Estrategia de selecao:\n"
            "  frequentes  — numeros que mais apareceram\n"
            "  atrasados   — numeros ausentes ha mais tempo\n"
            "  mista       — combina frequentes + atrasados (padrao)\n"
            "  equilibrada — balanca paridade e faixa"
        ),
    )
    p.add_argument("--jogos",          type=int, default=1,    help="Quantos jogos gerar (padrao: 1)")
    p.add_argument("--min-frequentes", type=int, default=2,    help="Min. de numeros frequentes (mista)")
    p.add_argument("--max-frequentes", type=int, default=4,    help="Max. de numeros frequentes (mista)")
    p.add_argument("--min-atrasados",  type=int, default=1,    help="Min. de numeros atrasados (mista)")
    p.add_argument("--max-atrasados",  type=int, default=3,    help="Max. de numeros atrasados (mista)")
    p.add_argument("--min-pares",      type=int, default=2,    help="Min. de numeros pares (equilibrada)")
    p.add_argument("--max-pares",      type=int, default=5,    help="Max. de numeros pares (equilibrada)")
    p.add_argument("--min-baixos",     type=int, default=2,    help="Min. de baixos 1-15 (equilibrada)")
    p.add_argument("--max-baixos",     type=int, default=5,    help="Max. de baixos 1-15 (equilibrada)")
    p.add_argument("--sem-metricas",   action="store_true",    help="Oculta o resumo de metricas")
    p.add_argument("--seed",           type=int, default=None, help="Semente aleatoria para reprodutibilidade")
    return p.parse_args()


def main():
    args = _parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    config = {
        "estrategia":     args.estrategia,
        "min_frequentes": args.min_frequentes,
        "max_frequentes": args.max_frequentes,
        "min_atrasados":  args.min_atrasados,
        "max_atrasados":  args.max_atrasados,
        "min_pares":      args.min_pares,
        "max_pares":      args.max_pares,
        "min_baixos":     args.min_baixos,
        "max_baixos":     args.max_baixos,
        "n_jogos":        args.jogos,
    }

    print(f"\nCarregando dados de: {args.dados!r} ...")
    try:
        historico = carregar_dados(args.dados)
    except (FileNotFoundError, ValueError) as e:
        print(f"ERRO: {e}")
        raise SystemExit(1)

    if not historico:
        print("ERRO: Nenhum concurso encontrado.")
        raise SystemExit(1)

    print(
        f"{len(historico)} concursos carregados"
        f" (#{historico[0]['concurso']} → #{historico[-1]['concurso']})"
    )

    metricas = calcular_metricas(historico)

    if not args.sem_metricas:
        exibir_metricas(metricas)

    n = config["n_jogos"]
    if n == 1:
        jogo = gerar_jogo(metricas, config)
        exibir_jogo(jogo)
    else:
        # Gera 3x mais candidatos para ter mais diversidade no ranking
        candidatos = gerar_e_ranquear(metricas, config, n_jogos=n * 3)
        melhores   = candidatos[:n]
        for i, j in enumerate(melhores, start=1):
            j["posicao"] = i
        exibir_ranking(melhores)
        print("--- Detalhes do melhor jogo ---")
        exibir_jogo(melhores[0], posicao=1)


if __name__ == "__main__":
    main()
