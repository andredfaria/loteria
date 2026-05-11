#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Análise de Pares e Ímpares - Lotofácil
=======================================

Este script percorre todos os concursos e verifica a quantidade de números
pares e ímpares sorteados em cada concurso.

IMPORTANTE: 
- Este é um sistema de análise estatística, SEM GARANTIA DE GANHO.
- A Lotofácil é um jogo de azar e cada sorteio é um evento independente.
- Não há métodos garantidos de ganho em jogos de loteria.
- Use com responsabilidade e dentro do seu orçamento pessoal.
"""

import json
import os
import sys
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
from pathlib import Path


# Configurações
DIRETORIO_DADOS = str(Path(__file__).resolve().parent.parent.parent / "dados")


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


def contar_pares_impares(dezenas: List[int]) -> Tuple[int, int, List[int], List[int]]:
    """
    Conta quantos números pares e ímpares foram sorteados.
    
    Args:
        dezenas: Lista de números sorteados
        
    Returns:
        Tupla com (quantidade_pares, quantidade_impares, lista_pares, lista_impares)
    """
    pares = [num for num in dezenas if num % 2 == 0]
    impares = [num for num in dezenas if num % 2 != 0]
    return len(pares), len(impares), sorted(pares), sorted(impares)


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


def analisar_pares_impares_todos_concursos() -> List[Dict]:
    """
    Percorre todos os concursos e analisa a quantidade de números pares e ímpares.
    
    Returns:
        Lista de dicionários com os resultados da análise de cada concurso
    """
    numeros_concursos = encontrar_arquivos_concursos()
    
    if not numeros_concursos:
        print("❌ Nenhum arquivo de concurso encontrado!", file=sys.stderr)
        return []
    
    resultados = []
    total = len(numeros_concursos)
    
    print(f"📊 Analisando {total} concursos...\n")
    
    for i, numero_concurso in enumerate(numeros_concursos, 1):
        concurso = carregar_concurso(numero_concurso)
        
        if not concurso:
            continue
        
        dezenas = extrair_dezenas(concurso)
        quantidade_pares, quantidade_impares, numeros_pares, numeros_impares = contar_pares_impares(dezenas)
        data = concurso.get("data", "N/A")
        
        resultado = {
            "concurso": numero_concurso,
            "data": data,
            "quantidade_pares": quantidade_pares,
            "quantidade_impares": quantidade_impares,
            "numeros_pares": numeros_pares,
            "numeros_impares": numeros_impares,
            "dezenas": sorted(dezenas)
        }
        
        resultados.append(resultado)
        
        # Progresso a cada 100 concursos
        if i % 100 == 0 or i == total:
            print(f"  Processados: {i}/{total} concursos", end="\r")
    
    print(f"\n✅ Análise concluída: {len(resultados)} concursos processados\n")
    return resultados


def gerar_estatisticas(resultados: List[Dict]) -> Dict:
    """
    Gera estatísticas sobre a quantidade de números pares e ímpares.
    
    Args:
        resultados: Lista com os resultados da análise de cada concurso
        
    Returns:
        Dicionário com as estatísticas geradas
    """
    if not resultados:
        return {}
    
    # Contar frequência de cada distribuição (pares, impares)
    distribuicao = defaultdict(int)
    for resultado in resultados:
        chave = (resultado["quantidade_pares"], resultado["quantidade_impares"])
        distribuicao[chave] += 1
    
    # Calcular médias
    total_concursos = len(resultados)
    soma_pares = sum(r["quantidade_pares"] for r in resultados)
    soma_impares = sum(r["quantidade_impares"] for r in resultados)
    media_pares = soma_pares / total_concursos if total_concursos > 0 else 0
    media_impares = soma_impares / total_concursos if total_concursos > 0 else 0
    
    # Encontrar mínimo e máximo
    quantidades_pares = [r["quantidade_pares"] for r in resultados]
    quantidades_impares = [r["quantidade_impares"] for r in resultados]
    min_pares = min(quantidades_pares)
    max_pares = max(quantidades_pares)
    min_impares = min(quantidades_impares)
    max_impares = max(quantidades_impares)
    
    estatisticas = {
        "total_concursos": total_concursos,
        "media_pares": media_pares,
        "media_impares": media_impares,
        "min_pares": min_pares,
        "max_pares": max_pares,
        "min_impares": min_impares,
        "max_impares": max_impares,
        "distribuicao": dict(distribuicao)
    }
    
    return estatisticas


def imprimir_resultados(resultados: List[Dict], estatisticas: Dict):
    """
    Imprime os resultados da análise de forma formatada.
    
    Args:
        resultados: Lista com os resultados da análise
        estatisticas: Dicionário com as estatísticas
    """
    print("=" * 80)
    print("ANÁLISE DE PARES E ÍMPARES - LOTOFÁCIL")
    print("=" * 80)
    print(f"\n📋 Análise: Quantidade de números pares e ímpares sorteados em cada concurso\n")
    
    # Estatísticas gerais
    print("📊 ESTATÍSTICAS GERAIS")
    print("-" * 80)
    print(f"Total de concursos analisados: {estatisticas['total_concursos']}")
    print(f"Média de números pares: {estatisticas['media_pares']:.2f}")
    print(f"Média de números ímpares: {estatisticas['media_impares']:.2f}")
    print(f"Mínimo de números pares: {estatisticas['min_pares']}")
    print(f"Máximo de números pares: {estatisticas['max_pares']}")
    print(f"Mínimo de números ímpares: {estatisticas['min_impares']}")
    print(f"Máximo de números ímpares: {estatisticas['max_impares']}")
    print()
    
    # Distribuição
    print("📈 DISTRIBUIÇÃO (Pares / Ímpares)")
    print("-" * 80)
    print(f"{'Pares/Ímpares':<15} {'Frequência':<12} {'Percentual':<12}")
    print("-" * 80)
    distribuicao_ordenada = sorted(estatisticas['distribuicao'].items(), key=lambda x: x[1], reverse=True)
    for (pares, impares), frequencia in distribuicao_ordenada:
        percentual = (frequencia / estatisticas['total_concursos']) * 100
        print(f"{pares:2d} pares / {impares:2d} ímpares  {frequencia:<12} {percentual:>10.2f}%")
    print()
    
    # Últimos 10 concursos
    print("📅 ÚLTIMOS 10 CONCURSOS")
    print("-" * 80)
    print(f"{'Concurso':<10} {'Data':<12} {'Pares':<8} {'Ímpares':<8} {'Distribuição':<30}")
    print("-" * 80)
    for resultado in resultados[-10:]:
        distribuicao_str = f"{resultado['quantidade_pares']}P/{resultado['quantidade_impares']}I"
        print(f"{resultado['concurso']:<10} {resultado['data']:<12} {resultado['quantidade_pares']:<8} {resultado['quantidade_impares']:<8} {distribuicao_str:<30}")
    print()
    
    # Concursos com mais pares
    print("🔵 TOP 10 CONCURSOS COM MAIS NÚMEROS PARES")
    print("-" * 80)
    print(f"{'Concurso':<10} {'Data':<12} {'Pares':<8} {'Ímpares':<8} {'Números Pares':<50}")
    print("-" * 80)
    top_pares = sorted(resultados, key=lambda x: x["quantidade_pares"], reverse=True)[:10]
    for resultado in top_pares:
        numeros_str = ", ".join(f"{n:02d}" for n in resultado["numeros_pares"])
        print(f"{resultado['concurso']:<10} {resultado['data']:<12} {resultado['quantidade_pares']:<8} {resultado['quantidade_impares']:<8} {numeros_str:<50}")
    print()
    
    # Concursos com mais ímpares
    print("🟡 TOP 10 CONCURSOS COM MAIS NÚMEROS ÍMPARES")
    print("-" * 80)
    print(f"{'Concurso':<10} {'Data':<12} {'Pares':<8} {'Ímpares':<8} {'Números Ímpares':<50}")
    print("-" * 80)
    top_impares = sorted(resultados, key=lambda x: x["quantidade_impares"], reverse=True)[:10]
    for resultado in top_impares:
        numeros_str = ", ".join(f"{n:02d}" for n in resultado["numeros_impares"])
        print(f"{resultado['concurso']:<10} {resultado['data']:<12} {resultado['quantidade_pares']:<8} {resultado['quantidade_impares']:<8} {numeros_str:<50}")
    print()
    
    # Concursos com menos pares
    print("📉 TOP 10 CONCURSOS COM MENOS NÚMEROS PARES")
    print("-" * 80)
    print(f"{'Concurso':<10} {'Data':<12} {'Pares':<8} {'Ímpares':<8} {'Números Pares':<50}")
    print("-" * 80)
    bottom_pares = sorted(resultados, key=lambda x: x["quantidade_pares"])[:10]
    for resultado in bottom_pares:
        numeros_str = ", ".join(f"{n:02d}" for n in resultado["numeros_pares"])
        print(f"{resultado['concurso']:<10} {resultado['data']:<12} {resultado['quantidade_pares']:<8} {resultado['quantidade_impares']:<8} {numeros_str:<50}")
    print()
    
    # Concursos com menos ímpares
    print("📉 TOP 10 CONCURSOS COM MENOS NÚMEROS ÍMPARES")
    print("-" * 80)
    print(f"{'Concurso':<10} {'Data':<12} {'Pares':<8} {'Ímpares':<8} {'Números Ímpares':<50}")
    print("-" * 80)
    bottom_impares = sorted(resultados, key=lambda x: x["quantidade_impares"])[:10]
    for resultado in bottom_impares:
        numeros_str = ", ".join(f"{n:02d}" for n in resultado["numeros_impares"])
        print(f"{resultado['concurso']:<10} {resultado['data']:<12} {resultado['quantidade_pares']:<8} {resultado['quantidade_impares']:<8} {numeros_str:<50}")
    print()
    
    # Exemplos detalhados das distribuições mais comuns
    print("🔍 EXEMPLOS DETALHADOS (Distribuições mais comuns)")
    print("-" * 80)
    distribuicao_ordenada = sorted(estatisticas['distribuicao'].items(), key=lambda x: x[1], reverse=True)
    top_distribuicoes = distribuicao_ordenada[:3]
    
    for (pares, impares), frequencia in top_distribuicoes:
        percentual = (frequencia / estatisticas['total_concursos']) * 100
        print(f"\n{pares} pares / {impares} ímpares ({frequencia} concursos - {percentual:.2f}%)")
        print("-" * 80)
        
        # Encontrar exemplos com essa distribuição
        exemplos = [r for r in resultados if r["quantidade_pares"] == pares and r["quantidade_impares"] == impares][:3]
        for exemplo in exemplos:
            pares_str = ", ".join(f"{n:02d}" for n in exemplo["numeros_pares"])
            impares_str = ", ".join(f"{n:02d}" for n in exemplo["numeros_impares"])
            print(f"  Concurso {exemplo['concurso']} ({exemplo['data']})")
            print(f"    Pares: {pares_str}")
            print(f"    Ímpares: {impares_str}")
    print()


def main():
    """Função principal"""
    # Verificar se o diretório existe
    if not os.path.exists(DIRETORIO_DADOS):
        print(f"❌ Diretório '{DIRETORIO_DADOS}' não encontrado!", file=sys.stderr)
        sys.exit(1)
    
    # Analisar todos os concursos
    resultados = analisar_pares_impares_todos_concursos()
    
    if not resultados:
        print("❌ Nenhum resultado encontrado!", file=sys.stderr)
        sys.exit(1)
    
    # Gerar estatísticas
    estatisticas = gerar_estatisticas(resultados)
    
    # Imprimir resultados
    imprimir_resultados(resultados, estatisticas)


if __name__ == "__main__":
    main()
