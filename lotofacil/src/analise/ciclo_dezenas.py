#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ciclo das Dezenas - Lotofácil
==============================

Este script implementa a estratégia do "Ciclo das Dezenas" descrita no
Relatório Técnico: Estratégias Racionais para a Lotofácil.

A estratégia consiste em analisar os últimos N concursos (padrão: 4) e
identificar quais números (1 a 25) ainda não foram sorteados nesse período.
Segundo o relatório, em média um ciclo completo de 25 dezenas se fecha a cada
4 concursos, e os números que estão "atrasados" têm uma probabilidade aumentada
de aparecer nos próximos sorteios.

IMPORTANTE: 
- Este é um sistema de análise estatística, SEM GARANTIA DE GANHO.
- A Lotofácil é um jogo de azar e cada sorteio é um evento independente.
- Não há métodos garantidos de ganho em jogos de loteria.
- Use com responsabilidade e dentro do seu orçamento pessoal.

Autor: Baseado no Relatório Técnico: Estratégias Racionais para a Lotofácil
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
from collections import defaultdict


# Configurações
DIRETORIO_DADOS = str(Path(__file__).resolve().parent.parent.parent / "dados")
TODOS_NUMEROS = list(range(1, 26))  # Números de 1 a 25


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


def carregar_concursos_periodo(concurso_referencia: int, num_concursos: int) -> List[Dict]:
    """
    Carrega os concursos de um período específico.
    
    Args:
        concurso_referencia: Número do concurso de referência
        num_concursos: Quantidade de concursos a carregar (incluindo o de referência)
        
    Returns:
        Lista de dicionários com os dados dos concursos carregados
    """
    concursos = []
    inicio = concurso_referencia - num_concursos + 1
    
    for num_concurso in range(inicio, concurso_referencia + 1):
        concurso = carregar_concurso(num_concurso)
        if concurso:
            concursos.append(concurso)
        else:
            print(f"Aviso: Concurso {num_concurso} não encontrado", file=sys.stderr)
    
    return concursos


def calcular_estatisticas(concursos_analisados: List[Dict], todos_numeros: List[int]) -> Dict:
    """
    Calcula estatísticas detalhadas para cada número no período analisado.
    
    Args:
        concursos_analisados: Lista de dicionários com dados dos concursos
        todos_numeros: Lista com todos os números possíveis (1-25)
        
    Returns:
        Dicionário com estatísticas por número
    """
    estatisticas = {}
    numeros_que_apareceram = set()
    
    # Inicializar estatísticas para todos os números
    for numero in todos_numeros:
        estatisticas[numero] = {
            "apareceu": False,
            "frequencia": 0,
            "ultimo_concurso": None,
            "concursos_que_apareceu": []
        }
    
    # Processar cada concurso
    for concurso in concursos_analisados:
        numero_concurso = concurso.get("concurso")
        dezenas = extrair_dezenas(concurso)
        
        for numero in dezenas:
            if numero in todos_numeros:
                numeros_que_apareceram.add(numero)
                estatisticas[numero]["apareceu"] = True
                estatisticas[numero]["frequencia"] += 1
                estatisticas[numero]["ultimo_concurso"] = numero_concurso
                estatisticas[numero]["concursos_que_apareceu"].append(numero_concurso)
    
    return estatisticas, numeros_que_apareceram


def analisar_ciclo_dezenas(concurso_referencia: int, num_concursos: int = 4) -> Dict:
    """
    Função principal que analisa o ciclo das dezenas.
    
    Args:
        concurso_referencia: Número do concurso de referência
        num_concursos: Quantidade de concursos anteriores para analisar (padrão: 4)
        
    Returns:
        Dicionário com análise detalhada do ciclo
    """
    # Carregar concursos do período
    concursos_analisados = carregar_concursos_periodo(concurso_referencia, num_concursos)
    
    if not concursos_analisados:
        raise ValueError(f"Nenhum concurso encontrado para análise. Verifique se os arquivos existem no diretório {DIRETORIO_DADOS}")
    
    # Ordenar por número de concurso
    concursos_analisados.sort(key=lambda x: x.get("concurso", 0))
    
    # Calcular estatísticas
    estatisticas_por_numero, numeros_que_apareceram = calcular_estatisticas(
        concursos_analisados, TODOS_NUMEROS
    )
    
    # Identificar números que não apareceram
    todos_numeros_set = set(TODOS_NUMEROS)
    numeros_nao_apareceram = todos_numeros_set - numeros_que_apareceram
    
    # Ordenar números recomendados
    numeros_recomendados = sorted(list(numeros_nao_apareceram))
    
    # Calcular cobertura do ciclo
    total_numeros_apareceram = len(numeros_que_apareceram)
    cobertura_ciclo = total_numeros_apareceram / len(TODOS_NUMEROS)
    
    # Lista de números dos concursos analisados
    numeros_concursos = [c.get("concurso") for c in concursos_analisados]
    
    # Montar resultado
    resultado = {
        "concurso_referencia": concurso_referencia,
        "concursos_analisados": numeros_concursos,
        "numeros_que_apareceram": sorted(list(numeros_que_apareceram)),
        "numeros_nao_apareceram": numeros_recomendados,
        "numeros_recomendados": numeros_recomendados,
        "cobertura_ciclo": cobertura_ciclo,
        "estatisticas_por_numero": estatisticas_por_numero,
        "resumo": {
            "total_numeros_apareceram": total_numeros_apareceram,
            "total_numeros_faltam": len(numeros_nao_apareceram),
            "concursos_analisados_count": len(concursos_analisados)
        }
    }
    
    return resultado


def formatar_saida(analise: Dict) -> str:
    """
    Formata os resultados da análise para exibição legível.
    
    Args:
        analise: Dicionário com os resultados da análise
        
    Returns:
        String formatada com os resultados
    """
    output = []
    output.append("=" * 70)
    output.append("ANÁLISE DO CICLO DAS DEZENAS - LOTOFÁCIL")
    output.append("=" * 70)
    output.append("")
    
    # Informações gerais
    output.append(f"Concurso de Referência: {analise['concurso_referencia']}")
    output.append(f"Concursos Analisados: {analise['resumo']['concursos_analisados_count']}")
    output.append(f"Período: {analise['concursos_analisados'][0]} a {analise['concursos_analisados'][-1]}")
    output.append("")
    
    # Resumo
    output.append("-" * 70)
    output.append("RESUMO DO CICLO")
    output.append("-" * 70)
    output.append(f"Números que apareceram: {analise['resumo']['total_numeros_apareceram']}/25")
    output.append(f"Números que NÃO apareceram: {analise['resumo']['total_numeros_faltam']}/25")
    output.append(f"Cobertura do ciclo: {analise['cobertura_ciclo']:.1%}")
    output.append("")
    
    # Números recomendados (que não apareceram)
    if analise['numeros_recomendados']:
        output.append("-" * 70)
        output.append("NÚMEROS RECOMENDADOS (não apareceram no período analisado)")
        output.append("-" * 70)
        numeros_formatados = [f"{n:02d}" for n in analise['numeros_recomendados']]
        output.append(" ".join(numeros_formatados))
        output.append(f"\nTotal: {len(analise['numeros_recomendados'])} números")
        output.append("")
    else:
        output.append("-" * 70)
        output.append("CICLO COMPLETO!")
        output.append("-" * 70)
        output.append("Todos os 25 números apareceram no período analisado.")
        output.append("")
    
    # Estatísticas detalhadas por número
    output.append("-" * 70)
    output.append("ESTATÍSTICAS DETALHADAS POR NÚMERO")
    output.append("-" * 70)
    output.append(f"{'Número':<8} {'Apareceu':<12} {'Frequência':<12} {'Último Concurso':<18}")
    output.append("-" * 70)
    
    for numero in sorted(TODOS_NUMEROS):
        stats = analise['estatisticas_por_numero'][numero]
        apareceu_str = "Sim" if stats['apareceu'] else "Não"
        frequencia = stats['frequencia']
        ultimo_concurso = stats['ultimo_concurso'] if stats['ultimo_concurso'] else "-"
        output.append(f"{numero:02d}      {apareceu_str:<12} {frequencia:<12} {ultimo_concurso}")
    
    output.append("")
    
    # Números que apareceram
    output.append("-" * 70)
    output.append(f"NÚMEROS QUE APARECERAM ({len(analise['numeros_que_apareceram'])} números)")
    output.append("-" * 70)
    numeros_apareceram_formatados = [f"{n:02d}" for n in analise['numeros_que_apareceram']]
    # Quebrar em linhas de 15 números para melhor visualização
    for i in range(0, len(numeros_apareceram_formatados), 15):
        linha = numeros_apareceram_formatados[i:i+15]
        output.append(" ".join(linha))
    output.append("")
    
    output.append("=" * 70)
    output.append("FIM DA ANÁLISE")
    output.append("=" * 70)
    
    return "\n".join(output)


def main():
    """Função principal com interface de linha de comando."""
    if len(sys.argv) < 2:
        print("Uso: python ciclo_dezenas.py <numero_concurso> [num_concursos]")
        print("")
        print("Exemplos:")
        print("  python ciclo_dezenas.py 3174")
        print("  python ciclo_dezenas.py 3174 4")
        print("")
        print("Parâmetros:")
        print("  numero_concurso: Número do concurso de referência (obrigatório)")
        print("  num_concursos:   Quantidade de concursos para analisar (padrão: 4)")
        sys.exit(1)
    
    try:
        concurso_referencia = int(sys.argv[1])
    except ValueError:
        print(f"Erro: '{sys.argv[1]}' não é um número válido de concurso", file=sys.stderr)
        sys.exit(1)
    
    num_concursos = 4  # Padrão
    if len(sys.argv) >= 3:
        try:
            num_concursos = int(sys.argv[2])
            if num_concursos < 1:
                print("Erro: O número de concursos deve ser maior que zero", file=sys.stderr)
                sys.exit(1)
        except ValueError:
            print(f"Erro: '{sys.argv[2]}' não é um número válido", file=sys.stderr)
            sys.exit(1)
    
    try:
        # Executar análise
        analise = analisar_ciclo_dezenas(concurso_referencia, num_concursos)
        
        # Exibir resultados
        resultado_formatado = formatar_saida(analise)
        print(resultado_formatado)
        
    except ValueError as e:
        print(f"Erro: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Erro inesperado: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
