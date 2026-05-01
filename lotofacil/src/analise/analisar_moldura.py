#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Análise da Moldura - Lotofácil
===============================

Este script percorre todos os concursos e verifica quantos números da moldura
foram sorteados em cada concurso.

A moldura consiste nos números das bordas do cartão da Lotofácil:
01, 02, 03, 04, 05, 06, 10, 11, 15, 16, 20, 21, 22, 23, 24, 25

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

# Números da moldura (bordas do cartão)
NUMEROS_MOLDURA = {1, 2, 3, 4, 5, 6, 10, 11, 15, 16, 20, 21, 22, 23, 24, 25}


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


def contar_moldura_sorteados(dezenas: List[int]) -> Tuple[int, List[int]]:
    """
    Conta quantos números da moldura foram sorteados.
    
    Args:
        dezenas: Lista de números sorteados
        
    Returns:
        Tupla com (quantidade de números da moldura, lista dos números da moldura sorteados)
    """
    moldura_sorteados = [num for num in dezenas if num in NUMEROS_MOLDURA]
    return len(moldura_sorteados), sorted(moldura_sorteados)


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


def analisar_moldura_todos_concursos() -> List[Dict]:
    """
    Percorre todos os concursos e analisa a quantidade de números da moldura sorteados.
    
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
        quantidade_moldura, numeros_moldura = contar_moldura_sorteados(dezenas)
        data = concurso.get("data", "N/A")
        
        resultado = {
            "concurso": numero_concurso,
            "data": data,
            "quantidade_moldura": quantidade_moldura,
            "numeros_moldura_sorteados": numeros_moldura,
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
    Gera estatísticas sobre a quantidade de números da moldura sorteados.
    
    Args:
        resultados: Lista com os resultados da análise de cada concurso
        
    Returns:
        Dicionário com as estatísticas geradas
    """
    if not resultados:
        return {}
    
    # Contar frequência de cada quantidade de números da moldura
    frequencias = defaultdict(int)
    for resultado in resultados:
        quantidade = resultado["quantidade_moldura"]
        frequencias[quantidade] += 1
    
    # Calcular média
    total_concursos = len(resultados)
    soma_total = sum(r["quantidade_moldura"] for r in resultados)
    media = soma_total / total_concursos if total_concursos > 0 else 0
    
    # Encontrar mínimo e máximo
    quantidades = [r["quantidade_moldura"] for r in resultados]
    minimo = min(quantidades)
    maximo = max(quantidades)
    
    # Contar concursos com cada quantidade
    distribuicao = {}
    for quantidade in range(minimo, maximo + 1):
        distribuicao[quantidade] = frequencias.get(quantidade, 0)
    
    estatisticas = {
        "total_concursos": total_concursos,
        "media": media,
        "minimo": minimo,
        "maximo": maximo,
        "distribuicao": distribuicao,
        "frequencias": dict(frequencias)
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
    print("ANÁLISE DA MOLDURA - LOTOFÁCIL")
    print("=" * 80)
    print(f"\n📋 Números da moldura: {sorted(NUMEROS_MOLDURA)}")
    print(f"   Total de números na moldura: {len(NUMEROS_MOLDURA)}\n")
    
    # Estatísticas gerais
    print("📊 ESTATÍSTICAS GERAIS")
    print("-" * 80)
    print(f"Total de concursos analisados: {estatisticas['total_concursos']}")
    print(f"Média de números da moldura sorteados: {estatisticas['media']:.2f}")
    print(f"Mínimo de números da moldura sorteados: {estatisticas['minimo']}")
    print(f"Máximo de números da moldura sorteados: {estatisticas['maximo']}")
    print()
    
    # Distribuição
    print("📈 DISTRIBUIÇÃO")
    print("-" * 80)
    print(f"{'Quantidade':<12} {'Frequência':<12} {'Percentual':<12}")
    print("-" * 80)
    for quantidade in sorted(estatisticas['distribuicao'].keys()):
        frequencia = estatisticas['distribuicao'][quantidade]
        percentual = (frequencia / estatisticas['total_concursos']) * 100
        print(f"{quantidade:<12} {frequencia:<12} {percentual:>10.2f}%")
    print()
    
    # Últimos 10 concursos
    print("📅 ÚLTIMOS 10 CONCURSOS")
    print("-" * 80)
    print(f"{'Concurso':<10} {'Data':<12} {'Qtd Moldura':<12} {'Números da Moldura':<30}")
    print("-" * 80)
    for resultado in resultados[-10:]:
        numeros_str = ", ".join(f"{n:02d}" for n in resultado["numeros_moldura_sorteados"])
        if not numeros_str:
            numeros_str = "Nenhum"
        print(f"{resultado['concurso']:<10} {resultado['data']:<12} {resultado['quantidade_moldura']:<12} {numeros_str:<30}")
    print()
    
    # Concursos com mais números da moldura
    print("🏆 TOP 10 CONCURSOS COM MAIS NÚMEROS DA MOLDURA")
    print("-" * 80)
    print(f"{'Concurso':<10} {'Data':<12} {'Qtd Moldura':<12} {'Números da Moldura':<30}")
    print("-" * 80)
    top_concursos = sorted(resultados, key=lambda x: x["quantidade_moldura"], reverse=True)[:10]
    for resultado in top_concursos:
        numeros_str = ", ".join(f"{n:02d}" for n in resultado["numeros_moldura_sorteados"])
        print(f"{resultado['concurso']:<10} {resultado['data']:<12} {resultado['quantidade_moldura']:<12} {numeros_str:<30}")
    print()
    
    # Concursos com menos números da moldura
    print("📉 TOP 10 CONCURSOS COM MENOS NÚMEROS DA MOLDURA")
    print("-" * 80)
    print(f"{'Concurso':<10} {'Data':<12} {'Qtd Moldura':<12} {'Números da Moldura':<30}")
    print("-" * 80)
    bottom_concursos = sorted(resultados, key=lambda x: x["quantidade_moldura"])[:10]
    for resultado in bottom_concursos:
        numeros_str = ", ".join(f"{n:02d}" for n in resultado["numeros_moldura_sorteados"])
        print(f"{resultado['concurso']:<10} {resultado['data']:<12} {resultado['quantidade_moldura']:<12} {numeros_str:<30}")
    print()


def main():
    """Função principal"""
    # Verificar se o diretório existe
    if not os.path.exists(DIRETORIO_DADOS):
        print(f"❌ Diretório '{DIRETORIO_DADOS}' não encontrado!", file=sys.stderr)
        sys.exit(1)
    
    # Analisar todos os concursos
    resultados = analisar_moldura_todos_concursos()
    
    if not resultados:
        print("❌ Nenhum resultado encontrado!", file=sys.stderr)
        sys.exit(1)
    
    # Gerar estatísticas
    estatisticas = gerar_estatisticas(resultados)
    
    # Imprimir resultados
    imprimir_resultados(resultados, estatisticas)


if __name__ == "__main__":
    main()
