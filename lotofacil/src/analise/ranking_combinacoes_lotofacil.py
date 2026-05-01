#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ranking de Combinações da Lotofácil por Acertos
================================================

Este script analisa o histórico da Lotofácil e exibe um ranking de combinações
de 15 números ordenado pela quantidade de concursos onde cada combinação
alcançou 15, 14, 13, 12 e 11 acertos.

IMPORTANTE: 
- Este é um sistema de análise estatística, SEM GARANTIA DE GANHO.
- A Lotofácil é um jogo de azar e cada sorteio é um evento independente.
- Não há métodos garantidos de ganho em jogos de loteria.
- Use com responsabilidade e dentro do seu orçamento pessoal.
"""

import json
import sys
import argparse
import time
import itertools
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple, Iterator
import pandas as pd


# Configurações
DIRETORIO_DADOS = str(Path(__file__).resolve().parent.parent.parent / "dados")
NUMEROS_LOTOFACIL = set(range(1, 26))  # Números de 1 a 25


def normalizar_combinacao(dezenas: List[str]) -> tuple:
    """
    Normaliza uma combinação de dezenas para uma tupla ordenada de inteiros.
    
    Args:
        dezenas: Lista de strings representando os números (ex: ["01", "02", ...])
        
    Returns:
        Tupla ordenada de inteiros (ex: (1, 2, 3, ..., 15))
    """
    return tuple(sorted(int(d) for d in dezenas))


def carregar_concursos(diretorio: str) -> List[Dict]:
    """
    Carrega todos os arquivos de concursos do diretório especificado.
    
    Args:
        diretorio: Caminho do diretório contendo os arquivos JSON dos concursos
        
    Returns:
        Lista de dicionários com os dados dos concursos
    """
    diretorio_path = Path(diretorio)
    if not diretorio_path.exists():
        print(f"❌ Diretório '{diretorio}' não encontrado!", file=sys.stderr)
        return []
    
    concursos = []
    arquivos = sorted(diretorio_path.glob("concurso_*.json"))
    
    print(f"📂 Carregando {len(arquivos)} arquivos de concursos...")
    
    for arquivo in arquivos:
        try:
            with open(arquivo, 'r', encoding='utf-8') as f:
                dados = json.load(f)
                concursos.append(dados)
        except (json.JSONDecodeError, IOError) as e:
            print(f"⚠️  Erro ao carregar {arquivo.name}: {e}", file=sys.stderr)
            continue
    
    return concursos


def gerar_combinacoes_14_acertos(sorteio: tuple, sorteio_set: set, numeros_nao_sorteados: set) -> Iterator[tuple]:
    """
    Gera todas as combinações que teriam exatamente 14 acertos com o sorteio dado.
    
    OTIMIZADO: Usa generator para evitar armazenar todas as combinações em memória.
    Para cada número sorteado, remove-o e adiciona cada número não sorteado.
    Isso gera 15 × 10 = 150 combinações distintas (algumas podem se repetir).
    
    Args:
        sorteio: Tupla ordenada com os 15 números sorteados
        sorteio_set: Set do sorteio (pré-calculado para otimização)
        numeros_nao_sorteados: Set de números não sorteados (pré-calculado)
        
    Yields:
        Tuplas ordenadas representando combinações com 14 acertos
    """
    # Criar lista de números não sorteados ordenada para inserção eficiente
    numeros_nao_sorteados_ord = sorted(numeros_nao_sorteados)
    
    for numero_remover in sorteio:
        # Criar lista sem o número removido (já está ordenada)
        temp_list = [n for n in sorteio if n != numero_remover]
        for numero_adicionar in numeros_nao_sorteados_ord:
            # Inserir o novo número mantendo a ordenação
            nova_lista = temp_list + [numero_adicionar]
            nova_lista.sort()
            yield tuple(nova_lista)


def gerar_combinacoes_13_acertos(sorteio: tuple, numeros_nao_sorteados: List[int]) -> Iterator[tuple]:
    """
    Gera todas as combinações que teriam exatamente 13 acertos com o sorteio dado.
    
    OTIMIZADO: Usa generator para evitar armazenar todas as combinações em memória.
    Para cada combinação de 13 números do sorteio, adiciona 2 números não sorteados.
    Isso gera C(15,13) × C(10,2) = 105 × 45 = 4.725 combinações por concurso.
    
    Args:
        sorteio: Tupla ordenada com os 15 números sorteados
        numeros_nao_sorteados: Lista de números não sorteados (pré-calculada)
        
    Yields:
        Tuplas ordenadas representando combinações com 13 acertos
    """
    # Para cada combinação de 13 números do sorteio
    for comb_13_sorteados in itertools.combinations(sorteio, 13):
        # Para cada combinação de 2 números não sorteados
        for comb_2_nao_sorteados in itertools.combinations(numeros_nao_sorteados, 2):
            # Mesclar e ordenar (sorteio já está ordenado, então só precisa mesclar)
            nova_lista = list(comb_13_sorteados) + list(comb_2_nao_sorteados)
            nova_lista.sort()
            yield tuple(nova_lista)


def gerar_combinacoes_12_acertos(sorteio: tuple, numeros_nao_sorteados: List[int]) -> Iterator[tuple]:
    """
    Gera todas as combinações que teriam exatamente 12 acertos com o sorteio dado.
    
    OTIMIZADO: Usa generator para evitar armazenar todas as combinações em memória.
    Para cada combinação de 12 números do sorteio, adiciona 3 números não sorteados.
    Isso gera C(15,12) × C(10,3) = 455 × 120 = 54.600 combinações por concurso.
    
    Args:
        sorteio: Tupla ordenada com os 15 números sorteados
        numeros_nao_sorteados: Lista de números não sorteados (pré-calculada)
        
    Yields:
        Tuplas ordenadas representando combinações com 12 acertos
    """
    # Para cada combinação de 12 números do sorteio
    for comb_12_sorteados in itertools.combinations(sorteio, 12):
        # Para cada combinação de 3 números não sorteados
        for comb_3_nao_sorteados in itertools.combinations(numeros_nao_sorteados, 3):
            # Mesclar e ordenar
            nova_lista = list(comb_12_sorteados) + list(comb_3_nao_sorteados)
            nova_lista.sort()
            yield tuple(nova_lista)


def gerar_combinacoes_11_acertos(sorteio: tuple, numeros_nao_sorteados: List[int]) -> Iterator[tuple]:
    """
    Gera todas as combinações que teriam exatamente 11 acertos com o sorteio dado.
    
    OTIMIZADO: Usa generator para evitar armazenar todas as combinações em memória.
    Para cada combinação de 11 números do sorteio, adiciona 4 números não sorteados.
    Isso gera C(15,11) × C(10,4) = 1.365 × 210 = 286.650 combinações por concurso.
    
    Args:
        sorteio: Tupla ordenada com os 15 números sorteados
        numeros_nao_sorteados: Lista de números não sorteados (pré-calculada)
        
    Yields:
        Tuplas ordenadas representando combinações com 11 acertos
    """
    # Para cada combinação de 11 números do sorteio
    for comb_11_sorteados in itertools.combinations(sorteio, 11):
        # Para cada combinação de 4 números não sorteados
        for comb_4_nao_sorteados in itertools.combinations(numeros_nao_sorteados, 4):
            # Mesclar e ordenar
            nova_lista = list(comb_11_sorteados) + list(comb_4_nao_sorteados)
            nova_lista.sort()
            yield tuple(nova_lista)


def processar_concursos(concursos: List[Dict]) -> Tuple[Dict[tuple, int], Dict[tuple, int], Dict[tuple, int], Dict[tuple, int], Dict[tuple, int]]:
    """
    Processa todos os concursos e conta quantas vezes cada combinação
    alcançou 15, 14, 13, 12 e 11 acertos.
    
    OTIMIZADO: Usa generators e cache de valores pré-calculados para reduzir
    uso de memória e melhorar performance.
    
    Args:
        concursos: Lista de dicionários com dados dos concursos
        
    Returns:
        Tupla (counts_15, counts_14, counts_13, counts_12, counts_11) onde cada
        dicionário mapeia combinação (tupla) -> número de concursos
    """
    counts_15 = defaultdict(int)
    counts_14 = defaultdict(int)
    counts_13 = defaultdict(int)
    counts_12 = defaultdict(int)
    counts_11 = defaultdict(int)
    
    print(f"\n🔄 Processando {len(concursos)} concursos...")
    inicio = time.time()
    
    for i, concurso in enumerate(concursos, 1):
        # Extrair dezenas do concurso
        dezenas_str = concurso.get("dezenas", [])
        if len(dezenas_str) != 15:
            continue
        
        # Normalizar sorteio
        sorteio = normalizar_combinacao(dezenas_str)
        
        # Pré-calcular valores para otimização (cache)
        sorteio_set = set(sorteio)
        numeros_nao_sorteados_set = NUMEROS_LOTOFACIL - sorteio_set
        numeros_nao_sorteados_list = sorted(numeros_nao_sorteados_set)
        
        # Incrementar contador de 15 acertos para a combinação sorteada
        counts_15[sorteio] += 1
        
        # Gerar combinações com 14 acertos e incrementar contadores (usando generator)
        for comb_14 in gerar_combinacoes_14_acertos(sorteio, sorteio_set, numeros_nao_sorteados_set):
            counts_14[comb_14] += 1
        
        # Gerar combinações com 13 acertos e incrementar contadores (usando generator)
        for comb_13 in gerar_combinacoes_13_acertos(sorteio, numeros_nao_sorteados_list):
            counts_13[comb_13] += 1
        
        # Gerar combinações com 12 acertos e incrementar contadores (usando generator)
        for comb_12 in gerar_combinacoes_12_acertos(sorteio, numeros_nao_sorteados_list):
            counts_12[comb_12] += 1
        
        # Gerar combinações com 11 acertos e incrementar contadores (usando generator)
        for comb_11 in gerar_combinacoes_11_acertos(sorteio, numeros_nao_sorteados_list):
            counts_11[comb_11] += 1
        
        # Progresso a cada 100 concursos
        if i % 100 == 0:
            tempo_decorrido = time.time() - inicio
            print(f"  Processados: {i}/{len(concursos)} concursos ({tempo_decorrido:.1f}s)", end="\r")
    
    tempo_total = time.time() - inicio
    print(f"\n✅ Processamento concluído em {tempo_total:.2f} segundos")
    
    return counts_15, counts_14, counts_13, counts_12, counts_11


def gerar_dataframe(counts_15: Dict[tuple, int], counts_14: Dict[tuple, int], 
                    counts_13: Dict[tuple, int], counts_12: Dict[tuple, int], 
                    counts_11: Dict[tuple, int]) -> pd.DataFrame:
    """
    Gera DataFrame com o ranking de combinações ordenado por acertos.
    
    OTIMIZADO: Usa set.update() para união eficiente e dict comprehension para
    criar registros de forma mais eficiente.
    
    Args:
        counts_15: Dicionário com contagem de 15 acertos por combinação
        counts_14: Dicionário com contagem de 14 acertos por combinação
        counts_13: Dicionário com contagem de 13 acertos por combinação
        counts_12: Dicionário com contagem de 12 acertos por combinação
        counts_11: Dicionário com contagem de 11 acertos por combinação
        
    Returns:
        DataFrame ordenado com colunas: combination, concurso_15, concurso_14, 
        concurso_13, concurso_12, concurso_11, concurso_total
    """
    # Unir todas as combinações únicas usando set.update() (mais eficiente)
    todas_combinacoes = set(counts_15.keys())
    todas_combinacoes.update(counts_14.keys())
    todas_combinacoes.update(counts_13.keys())
    todas_combinacoes.update(counts_12.keys())
    todas_combinacoes.update(counts_11.keys())
    
    print(f"\n📊 Consolidando {len(todas_combinacoes)} combinações únicas...")
    
    # Criar lista de registros usando list comprehension (mais eficiente)
    registros = []
    for comb in todas_combinacoes:
        concurso_15 = counts_15.get(comb, 0)
        concurso_14 = counts_14.get(comb, 0)
        concurso_13 = counts_13.get(comb, 0)
        concurso_12 = counts_12.get(comb, 0)
        concurso_11 = counts_11.get(comb, 0)
        concurso_total = concurso_15 + concurso_14 + concurso_13 + concurso_12 + concurso_11
        
        # Formatar combinação como string (ex: "01,02,03,...,15")
        comb_str = ",".join(f"{n:02d}" for n in comb)
        
        registros.append({
            "combination": comb_str,
            "concurso_15": concurso_15,
            "concurso_14": concurso_14,
            "concurso_13": concurso_13,
            "concurso_12": concurso_12,
            "concurso_11": concurso_11,
            "concurso_total": concurso_total
        })
    
    # Criar DataFrame
    df = pd.DataFrame(registros)
    
    # Ordenar por concurso_15 DESC, depois por concurso_14 DESC, etc.
    df = df.sort_values(
        by=["concurso_15", "concurso_14", "concurso_13", "concurso_12", "concurso_11"],
        ascending=[False, False, False, False, False]
    ).reset_index(drop=True)
    
    return df


def exibir_estatisticas(df: pd.DataFrame, tempo_total: float) -> None:
    """
    Exibe estatísticas sobre a análise realizada.
    
    Args:
        df: DataFrame com o ranking
        tempo_total: Tempo total de execução em segundos
    """
    print("\n" + "=" * 80)
    print("ESTATÍSTICAS DA ANÁLISE")
    print("=" * 80)
    print(f"Tempo de execução: {tempo_total:.2f} segundos")
    print(f"Combinações únicas analisadas: {len(df):,}")
    print(f"Combinações com 15 acertos: {(df['concurso_15'] > 0).sum():,}")
    print(f"Combinações com 14 acertos: {(df['concurso_14'] > 0).sum():,}")
    print(f"Combinações com 13 acertos: {(df['concurso_13'] > 0).sum():,}")
    print(f"Combinações com 12 acertos: {(df['concurso_12'] > 0).sum():,}")
    print(f"Combinações com 11 acertos: {(df['concurso_11'] > 0).sum():,}")
    print(f"Maior número de concursos com 15 acertos: {df['concurso_15'].max()}")
    print(f"Maior número de concursos com 14 acertos: {df['concurso_14'].max()}")
    print(f"Maior número de concursos com 13 acertos: {df['concurso_13'].max()}")
    print(f"Maior número de concursos com 12 acertos: {df['concurso_12'].max()}")
    print(f"Maior número de concursos com 11 acertos: {df['concurso_11'].max()}")
    print("=" * 80)


def exibir_top_n(df: pd.DataFrame, top_n: int) -> None:
    """
    Exibe as top N combinações do ranking.
    
    OTIMIZADO: Usa itertuples() em vez de iterrows() para melhor performance.
    
    Args:
        df: DataFrame com o ranking ordenado
        top_n: Número de combinações a exibir
    """
    top_df = df.head(top_n)
    
    print(f"\n🏆 TOP {len(top_df)} COMBINAÇÕES")
    print("=" * 120)
    print(f"{'Pos':<5} {'Combinação':<35} {'15':<8} {'14':<8} {'13':<8} {'12':<8} {'11':<8} {'Total':<8}")
    print("-" * 120)
    
    # Usar itertuples() em vez de iterrows() (muito mais rápido)
    for pos, row in enumerate(top_df.itertuples(), 1):
        comb = row.combination
        conc_15 = row.concurso_15
        conc_14 = row.concurso_14
        conc_13 = row.concurso_13
        conc_12 = row.concurso_12
        conc_11 = row.concurso_11
        total = row.concurso_total
                
        print(f"{pos:<5} {comb:<35} {conc_15:<8,} {conc_14:<8,} {conc_13:<8,} {conc_12:<8,} {conc_11:<8,} {total:<8,}")
    
    print("=" * 120)


def main():
    """Função principal"""
    parser = argparse.ArgumentParser(
        description="Analisa histórico da Lotofácil e gera ranking de combinações por acertos",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:
  # Mostrar top 50 combinações (padrão)
  python3 ranking_combinacoes_lotofacil.py
  
  # Mostrar top 100 combinações
  python3 ranking_combinacoes_lotofacil.py --top 100
  
  # Mostrar top 20 combinações
  python3 ranking_combinacoes_lotofacil.py -t 20
        """
    )
    
    parser.add_argument(
        '--top', '-t',
        type=int,
        default=50,
        help='Quantos resultados mostrar no ranking (padrão: 50)'
    )
    
    parser.add_argument(
        '--diretorio', '-d',
        type=str,
        default=DIRETORIO_DADOS,
        help=f'Diretório com os arquivos JSON dos concursos (padrão: {DIRETORIO_DADOS})'
    )
    
    args = parser.parse_args()
    
    # Validar argumentos
    if args.top < 1:
        print("❌ Erro: O número de resultados deve ser pelo menos 1!", file=sys.stderr)
        sys.exit(1)
    
    inicio_total = time.time()
    
    try:
        # Carregar concursos
        concursos = carregar_concursos(args.diretorio)
        
        if not concursos:
            print("❌ Nenhum concurso encontrado!", file=sys.stderr)
            sys.exit(1)
        
        # Processar concursos e contar acertos
        counts_15, counts_14, counts_13, counts_12, counts_11 = processar_concursos(concursos)
        
        # Gerar DataFrame com ranking
        df = gerar_dataframe(counts_15, counts_14, counts_13, counts_12, counts_11)
        
        # Exibir estatísticas
        tempo_total = time.time() - inicio_total
        exibir_estatisticas(df, tempo_total)
        
        # Exibir top N
        exibir_top_n(df, args.top)
        
    except Exception as e:
        print(f"❌ Erro inesperado: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
