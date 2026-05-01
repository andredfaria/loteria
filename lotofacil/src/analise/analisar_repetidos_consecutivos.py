#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Análise de Dezenas Repetidas - Lotofácil
=========================================

Este script percorre todos os concursos e verifica quantas dezenas se repetiram
em relação ao sorteio anterior (concurso consecutivo).

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


def contar_repetidos(dezenas_atual: List[int], dezenas_anterior: List[int]) -> Tuple[int, List[int]]:
    """
    Conta quantas dezenas se repetiram entre dois concursos consecutivos.
    
    Args:
        dezenas_atual: Lista de números sorteados no concurso atual
        dezenas_anterior: Lista de números sorteados no concurso anterior
        
    Returns:
        Tupla com (quantidade de números repetidos, lista dos números repetidos)
    """
    set_atual = set(dezenas_atual)
    set_anterior = set(dezenas_anterior)
    repetidos = set_atual.intersection(set_anterior)
    return len(repetidos), sorted(list(repetidos))


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


def analisar_repetidos_todos_concursos() -> List[Dict]:
    """
    Percorre todos os concursos e analisa a quantidade de dezenas repetidas
    em relação ao concurso anterior.
    
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
    
    dezenas_anterior = None
    concurso_anterior_num = None
    concurso_anterior_data = None
    
    for i, numero_concurso in enumerate(numeros_concursos, 1):
        concurso = carregar_concurso(numero_concurso)
        
        if not concurso:
            continue
        
        dezenas_atual = extrair_dezenas(concurso)
        data_atual = concurso.get("data", "N/A")
        
        # Para o primeiro concurso, não há repetidos
        if dezenas_anterior is None:
            resultado = {
                "concurso": numero_concurso,
                "data": data_atual,
                "concurso_anterior": None,
                "data_anterior": None,
                "quantidade_repetidos": 0,
                "numeros_repetidos": [],
                "dezenas_atual": sorted(dezenas_atual),
                "dezenas_anterior": []
            }
            resultados.append(resultado)
        else:
            # Comparar com o concurso anterior
            quantidade_repetidos, numeros_repetidos = contar_repetidos(dezenas_atual, dezenas_anterior)
            
            resultado = {
                "concurso": numero_concurso,
                "data": data_atual,
                "concurso_anterior": concurso_anterior_num,
                "data_anterior": concurso_anterior_data,
                "quantidade_repetidos": quantidade_repetidos,
                "numeros_repetidos": numeros_repetidos,
                "dezenas_atual": sorted(dezenas_atual),
                "dezenas_anterior": sorted(dezenas_anterior)
            }
            resultados.append(resultado)
        
        # Atualizar para o próximo concurso
        dezenas_anterior = dezenas_atual
        concurso_anterior_num = numero_concurso
        concurso_anterior_data = data_atual
        
        # Progresso a cada 100 concursos
        if i % 100 == 0 or i == total:
            print(f"  Processados: {i}/{total} concursos", end="\r")
    
    print(f"\n✅ Análise concluída: {len(resultados)} concursos processados\n")
    return resultados


def gerar_estatisticas(resultados: List[Dict]) -> Dict:
    """
    Gera estatísticas sobre a quantidade de dezenas repetidas entre concursos consecutivos.
    
    Args:
        resultados: Lista com os resultados da análise de cada concurso
        
    Returns:
        Dicionário com as estatísticas geradas
    """
    if not resultados:
        return {}
    
    # Filtrar o primeiro concurso (que não tem repetidos)
    resultados_com_repetidos = [r for r in resultados if r["concurso_anterior"] is not None]
    
    if not resultados_com_repetidos:
        return {}
    
    # Contar frequência de cada quantidade de números repetidos
    frequencias = defaultdict(int)
    for resultado in resultados_com_repetidos:
        quantidade = resultado["quantidade_repetidos"]
        frequencias[quantidade] += 1
    
    # Calcular média
    total_concursos = len(resultados_com_repetidos)
    soma_total = sum(r["quantidade_repetidos"] for r in resultados_com_repetidos)
    media = soma_total / total_concursos if total_concursos > 0 else 0
    
    # Encontrar mínimo e máximo
    quantidades = [r["quantidade_repetidos"] for r in resultados_com_repetidos]
    minimo = min(quantidades)
    maximo = max(quantidades)
    
    # Contar concursos com cada quantidade
    distribuicao = {}
    for quantidade in range(minimo, maximo + 1):
        distribuicao[quantidade] = frequencias.get(quantidade, 0)
    
    estatisticas = {
        "total_concursos": len(resultados),
        "total_concursos_com_repetidos": total_concursos,
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
    print("ANÁLISE DE DEZENAS REPETIDAS ENTRE SORTEIOS CONSECUTIVOS - LOTOFÁCIL")
    print("=" * 80)
    print(f"\n📋 Análise: Quantidade de dezenas que se repetem do concurso anterior\n")
    
    # Estatísticas gerais
    print("📊 ESTATÍSTICAS GERAIS")
    print("-" * 80)
    print(f"Total de concursos analisados: {estatisticas['total_concursos']}")
    print(f"Total de comparações (excluindo primeiro): {estatisticas['total_concursos_com_repetidos']}")
    print(f"Média de dezenas repetidas: {estatisticas['media']:.2f}")
    print(f"Mínimo de dezenas repetidas: {estatisticas['minimo']}")
    print(f"Máximo de dezenas repetidas: {estatisticas['maximo']}")
    print()
    
    # Distribuição
    print("📈 DISTRIBUIÇÃO")
    print("-" * 80)
    print(f"{'Quantidade':<12} {'Frequência':<12} {'Percentual':<12}")
    print("-" * 80)
    for quantidade in sorted(estatisticas['distribuicao'].keys()):
        frequencia = estatisticas['distribuicao'][quantidade]
        percentual = (frequencia / estatisticas['total_concursos_com_repetidos']) * 100
        print(f"{quantidade:<12} {frequencia:<12} {percentual:>10.2f}%")
    print()
    
    # Últimos 10 concursos
    print("📅 ÚLTIMOS 10 CONCURSOS")
    print("-" * 80)
    print(f"{'Concurso':<10} {'Data':<12} {'Qtd Repet':<10} {'Dezenas Repetidas':<50}")
    print("-" * 80)
    for resultado in resultados[-10:]:
        if resultado["concurso_anterior"] is None:
            numeros_str = "Primeiro concurso"
        else:
            numeros_str = ", ".join(f"{n:02d}" for n in resultado["numeros_repetidos"])
            if not numeros_str:
                numeros_str = "Nenhuma"
        print(f"{resultado['concurso']:<10} {resultado['data']:<12} {resultado['quantidade_repetidos']:<10} {numeros_str:<50}")
    print()
    
    # Concursos com mais repetidos
    print("🏆 TOP 10 CONCURSOS COM MAIS DEZENAS REPETIDAS")
    print("-" * 80)
    print(f"{'Concurso':<10} {'Data':<12} {'Anterior':<10} {'Qtd Repet':<10} {'Dezenas Repetidas':<50}")
    print("-" * 80)
    resultados_com_repetidos = [r for r in resultados if r["concurso_anterior"] is not None]
    top_concursos = sorted(resultados_com_repetidos, key=lambda x: x["quantidade_repetidos"], reverse=True)[:10]
    for resultado in top_concursos:
        numeros_str = ", ".join(f"{n:02d}" for n in resultado["numeros_repetidos"])
        print(f"{resultado['concurso']:<10} {resultado['data']:<12} {resultado['concurso_anterior']:<10} {resultado['quantidade_repetidos']:<10} {numeros_str:<50}")
    print()
    
    # Concursos com menos repetidos
    print("📉 TOP 10 CONCURSOS COM MENOS DEZENAS REPETIDAS")
    print("-" * 80)
    print(f"{'Concurso':<10} {'Data':<12} {'Anterior':<10} {'Qtd Repet':<10} {'Dezenas Repetidas':<50}")
    print("-" * 80)
    bottom_concursos = sorted(resultados_com_repetidos, key=lambda x: x["quantidade_repetidos"])[:10]
    for resultado in bottom_concursos:
        numeros_str = ", ".join(f"{n:02d}" for n in resultado["numeros_repetidos"])
        print(f"{resultado['concurso']:<10} {resultado['data']:<12} {resultado['concurso_anterior']:<10} {resultado['quantidade_repetidos']:<10} {numeros_str:<50}")
    print()
    
    # Exemplos detalhados
    print("🔍 EXEMPLOS DETALHADOS (Últimos 5 com mais repetidos)")
    print("-" * 80)
    exemplos = sorted(resultados_com_repetidos, key=lambda x: x["quantidade_repetidos"], reverse=True)[:5]
    for resultado in exemplos:
        print(f"\nConcurso {resultado['concurso']} ({resultado['data']}) vs Concurso {resultado['concurso_anterior']} ({resultado['data_anterior']})")
        print(f"  Dezenas repetidas ({resultado['quantidade_repetidos']}): {', '.join(f'{n:02d}' for n in resultado['numeros_repetidos'])}")
        print(f"  Dezenas do concurso {resultado['concurso']}: {', '.join(f'{n:02d}' for n in resultado['dezenas_atual'])}")
        print(f"  Dezenas do concurso {resultado['concurso_anterior']}: {', '.join(f'{n:02d}' for n in resultado['dezenas_anterior'])}")
    print()


def main():
    """Função principal"""
    # Verificar se o diretório existe
    if not os.path.exists(DIRETORIO_DADOS):
        print(f"❌ Diretório '{DIRETORIO_DADOS}' não encontrado!", file=sys.stderr)
        sys.exit(1)
    
    # Analisar todos os concursos
    resultados = analisar_repetidos_todos_concursos()
    
    if not resultados:
        print("❌ Nenhum resultado encontrado!", file=sys.stderr)
        sys.exit(1)
    
    # Gerar estatísticas
    estatisticas = gerar_estatisticas(resultados)
    
    if not estatisticas:
        print("❌ Não foi possível gerar estatísticas!", file=sys.stderr)
        sys.exit(1)
    
    # Imprimir resultados
    imprimir_resultados(resultados, estatisticas)


if __name__ == "__main__":
    main()
