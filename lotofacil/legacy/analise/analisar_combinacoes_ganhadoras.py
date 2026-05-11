#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Análise de Combinações Mais Premiada - Lotofácil
=================================================

Este script analisa o histórico da Lotofácil e agrega por combinação de 15 números,
contando matematicamente em quantos concursos cada combinação teria obtido 15 pontos
(combinação sorteada exata) e 14 pontos (compartilha exatamente 14 números com o sorteio),
apresentando um ranking detalhado.

IMPORTANTE: 
- Este é um sistema de análise estatística, SEM GARANTIA DE GANHO.
- A Lotofácil é um jogo de azar e cada sorteio é um evento independente.
- Não há métodos garantidos de ganho em jogos de loteria.
- Use com responsabilidade e dentro do seu orçamento pessoal.
"""

import json
import os
import sys
import argparse
from typing import Dict, List, Optional, Tuple, Set
from pathlib import Path
from collections import defaultdict
import pandas as pd


# Configurações
DIRETORIO_DADOS = str(Path(__file__).resolve().parent.parent.parent / "dados")
NUMEROS_LOTOFACIL = set(range(1, 26))  # Números de 1 a 25


def carregar_concurso(numero_concurso: int) -> Optional[Dict]:
    """
    Carrega um arquivo JSON de um concurso específico.
    
    Args:
        numero_concurso: Número do concurso a ser carregado
        
    Returns:
        Dicionário com os dados do concurso ou None se não encontrado
    """
    arquivo = os.path.join(DIRETORIO_DADOS, f"concurso_{numero_concurso}.json")
    
    if not os.path.exists(arquivo):
        return None
    
    try:
        with open(arquivo, 'r', encoding='utf-8') as f:
            dados = json.load(f)
        return dados
    except (json.JSONDecodeError, IOError) as e:
        print(f"Erro ao carregar concurso {numero_concurso}: {e}", file=sys.stderr)
        return None


def encontrar_arquivos_concursos() -> List[int]:
    """
    Encontra todos os arquivos de concursos e retorna uma lista ordenada dos números.
    
    Returns:
        Lista ordenada com os números dos concursos disponíveis
    """
    diretorio = Path(DIRETORIO_DADOS)
    if not diretorio.exists():
        print(f"❌ Diretório '{DIRETORIO_DADOS}' não encontrado!", file=sys.stderr)
        return []
    
    arquivos = sorted(diretorio.glob("concurso_*.json"))
    numeros_concursos = []
    
    for arquivo in arquivos:
        try:
            # Extrai o número do concurso do nome do arquivo (ex: concurso_2500.json -> 2500)
            numero = int(arquivo.stem.split("_")[1])
            numeros_concursos.append(numero)
        except (ValueError, IndexError):
            continue
    
    return sorted(numeros_concursos)


def extrair_dezenas(concurso: Dict) -> List[int]:
    """
    Extrai as dezenas sorteadas de um concurso e converte para inteiros.
    
    Args:
        concurso: Dicionário com os dados do concurso
        
    Returns:
        Lista de inteiros representando as dezenas sorteadas
    """
    dezenas_str = concurso.get("dezenas", [])
    return [int(d) for d in dezenas_str]


def normalizar_combinacao(dezenas: List[int]) -> tuple:
    """
    Normaliza uma combinação de dezenas para uma tupla ordenada de inteiros.
    Remove duplicatas e valida que tem exatamente 15 números.
    
    Args:
        dezenas: Lista de inteiros representando os números
        
    Returns:
        Tupla ordenada de inteiros (ex: (1, 2, 3, ..., 15))
    """
    # Remover duplicatas e ordenar
    dezenas_unicas = sorted(set(dezenas))
    
    # Validar que tem 15 números
    if len(dezenas_unicas) != 15:
        raise ValueError(f"Combinação deve ter exatamente 15 números, encontrados {len(dezenas_unicas)}")
    
    return tuple(dezenas_unicas)


def gerar_combinacoes_14_acertos(sorteio: tuple) -> Set[tuple]:
    """
    Gera todas as combinações que teriam exatamente 14 acertos com o sorteio dado.
    
    Para cada número sorteado, remove-o e adiciona cada número não sorteado.
    Isso gera até 15 × 10 = 150 combinações distintas por concurso.
    
    Args:
        sorteio: Tupla ordenada com os 15 números sorteados
        
    Returns:
        Conjunto de tuplas ordenadas representando combinações com 14 acertos
    """
    combinacoes_14 = set()
    numeros_nao_sorteados = NUMEROS_LOTOFACIL - set(sorteio)
    
    # Para cada número sorteado, remover e adicionar cada número não sorteado
    for numero_remover in sorteio:
        for numero_adicionar in numeros_nao_sorteados:
            # Remover número sorteado e adicionar número não sorteado
            nova_combinacao = tuple(sorted(set(sorteio) - {numero_remover} | {numero_adicionar}))
            combinacoes_14.add(nova_combinacao)
    
    return combinacoes_14


def analisar_combinacoes_ganhadoras() -> pd.DataFrame:
    """
    Processa todos os concursos e agrega por combinação de 15 números.
    Conta, para cada combinação, em quantos concursos ela obteve 15 e 14 acertos.
    
    Returns:
        DataFrame com colunas: combination, concurso_15, concurso_14, concurso_total
        Ordenado por concurso_15 DESC, depois concurso_14 DESC
    """
    numeros_concursos = encontrar_arquivos_concursos()
    counts_15 = defaultdict(int)
    counts_14 = defaultdict(int)
    
    print(f"🔍 Analisando concursos da Lotofácil...")
    print(f"📊 Processando {len(numeros_concursos)} concursos...\n")
    
    for i, numero_concurso in enumerate(numeros_concursos, 1):
        concurso = carregar_concurso(numero_concurso)
        
        if not concurso:
            continue
        
        # Extrair e normalizar dezenas
        try:
            dezenas = extrair_dezenas(concurso)
            sorteio = normalizar_combinacao(dezenas)
        except (ValueError, TypeError) as e:
            # Ignorar concursos com dados inválidos
            continue
        
        # Incrementar contador de 15 acertos para a combinação sorteada
        counts_15[sorteio] += 1
        
        # Gerar todas as combinações que teriam 14 acertos neste concurso
        combinacoes_14 = gerar_combinacoes_14_acertos(sorteio)
        
        # Incrementar contador de 14 acertos (evitar duplicatas usando set)
        for comb_14 in combinacoes_14:
            counts_14[comb_14] += 1
        
        # Progresso a cada 100 concursos
        if i % 100 == 0:
            print(f"  Processados: {i}/{len(numeros_concursos)} concursos", end="\r")
    
    print(f"\n✅ Processamento concluído!\n")
    
    # Consolidar resultados em DataFrame
    todas_combinacoes = set(counts_15.keys()) | set(counts_14.keys())
    
    print(f"📊 Consolidando {len(todas_combinacoes)} combinações únicas...")
    
    registros = []
    for comb in todas_combinacoes:
        concurso_15 = counts_15.get(comb, 0)
        concurso_14 = counts_14.get(comb, 0)
        concurso_total = concurso_15 + concurso_14
        
        # Filtrar apenas combinações com pelo menos uma ocorrência
        if concurso_total > 0:
            # Formatar combinação como string (ex: "01,02,03,...,15")
            comb_str = ",".join(f"{n:02d}" for n in comb)
            
            registros.append({
                "combination": comb_str,
                "concurso_15": concurso_15,
                "concurso_14": concurso_14,
                "concurso_total": concurso_total
            })
    
    # Criar DataFrame
    df = pd.DataFrame(registros)
    
    # Ordenar por concurso_15 DESC, depois por concurso_14 DESC
    df = df.sort_values(
        by=["concurso_15", "concurso_14"],
        ascending=[False, False]
    ).reset_index(drop=True)
    
    print(f"   Total de combinações únicas com acertos: {len(df):,}\n")
    
    return df


def gerar_relatorio(df: pd.DataFrame, top_n: int = 20) -> None:
    """
    Formata e imprime ranking com informações detalhadas.
    
    Args:
        df: DataFrame com colunas: combination, concurso_15, concurso_14, concurso_total
        top_n: Quantos resultados mostrar no ranking
    """
    if df.empty:
        print("❌ Nenhum resultado encontrado!")
        return
    
    print("=" * 80)
    print("ANÁLISE DE COMBINAÇÕES MAIS PREMIADA - LOTOFÁCIL")
    print("=" * 80)
    
    # Calcular estatísticas gerais
    total_combinacoes = len(df)
    combinacoes_com_15 = (df['concurso_15'] > 0).sum()
    combinacoes_com_14 = (df['concurso_14'] > 0).sum()
    combinacoes_com_ambos = ((df['concurso_15'] > 0) & (df['concurso_14'] > 0)).sum()
    
    print("\n📊 ESTATÍSTICAS GERAIS")
    print("-" * 80)
    print(f"Total de combinações únicas analisadas: {total_combinacoes:,}")
    print(f"Combinações com 15 acertos: {combinacoes_com_15:,}")
    print(f"Combinações com 14 acertos: {combinacoes_com_14:,}")
    print(f"Combinações com ambos (15 e 14): {combinacoes_com_ambos:,}")
    print(f"Maior número de concursos com 15 acertos: {df['concurso_15'].max()}")
    print(f"Maior número de concursos com 14 acertos: {df['concurso_14'].max()}")
    print()
    
    # Top N combinações
    top_df = df.head(top_n)
    
    print(f"🏆 TOP {len(top_df)} COMBINAÇÕES MAIS PREMIADAS")
    print("=" * 80)
    print(f"{'Pos':<5} {'Combinação':<45} {'Conc. 15':<12} {'Conc. 14':<12} {'Total':<12}")
    print("-" * 80)
    
    for idx, row in top_df.iterrows():
        pos = idx + 1
        comb = row['combination']
        conc_15 = row['concurso_15']
        conc_14 = row['concurso_14']
        total = row['concurso_total']
        
        # Truncar combinação se muito longa
        comb_display = comb if len(comb) <= 43 else comb[:40] + "..."
        
        print(f"{pos:<5} {comb_display:<45} {conc_15:<12,} {conc_14:<12,} {total:<12,}")
    
    print("=" * 80)
    print()


def main():
    """Função principal"""
    parser = argparse.ArgumentParser(
        description="Analisa combinações de 15 números mais premiadas da Lotofácil",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:
  # Mostrar top 20 combinações mais premiadas (padrão)
  python3 analisar_combinacoes_ganhadoras.py
  
  # Mostrar top 50 combinações
  python3 analisar_combinacoes_ganhadoras.py --top 50
  
  # Mostrar top 10 combinações
  python3 analisar_combinacoes_ganhadoras.py -t 10
  
  # Salvar em arquivo CSV específico
  python3 analisar_combinacoes_ganhadoras.py --save resultado.csv
        """
    )
    
    parser.add_argument(
        '--top', '-t',
        type=int,
        default=20,
        help='Quantos resultados mostrar no ranking (padrão: 20)'
    )
    
    parser.add_argument(
        '--save', '-s',
        type=str,
        default='ranking_combinacoes_lotofacil.csv',
        help='Caminho do arquivo CSV de saída (padrão: ranking_combinacoes_lotofacil.csv)'
    )
    
    args = parser.parse_args()
    
    # Validar argumentos
    if args.top < 1:
        print("❌ Erro: O número de resultados deve ser pelo menos 1!", file=sys.stderr)
        sys.exit(1)
    
    # Verificar se o diretório existe
    if not os.path.exists(DIRETORIO_DADOS):
        print(f"❌ Diretório '{DIRETORIO_DADOS}' não encontrado!", file=sys.stderr)
        sys.exit(1)
    
    try:
        # Analisar combinações ganhadoras
        df = analisar_combinacoes_ganhadoras()
        
        # Gerar relatório
        gerar_relatorio(df, args.top)
        
        # Salvar CSV
        print(f"💾 Salvando ranking completo em '{args.save}'...")
        df.to_csv(args.save, index=False, encoding='utf-8')
        print(f"✅ Arquivo '{args.save}' salvo com sucesso!")
        print(f"   Total de registros: {len(df):,}\n")
        
    except Exception as e:
        print(f"❌ Erro inesperado: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
