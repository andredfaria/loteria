#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validador de Jogos Prováveis - Lotofácil
=========================================

Este script valida jogos prováveis comparando-os com as dezenas sorteadas
de um concurso específico, exibindo quantos acertos cada jogo teve.

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
from pathlib import Path
from typing import List, Dict, Optional
from collections import Counter

# Diretórios
_ROOT = Path(__file__).resolve().parent.parent.parent
DIRETORIO_JOGOS_GERADOS = str(_ROOT / "saida" / "jogos")
DIRETORIO_DADOS = str(_ROOT / "dados")


def carregar_jogos_provaveis(id_jogo: int) -> Optional[List[List[str]]]:
    """
    Carrega jogos prováveis do arquivo JSON.
    
    Args:
        id_jogo: ID do jogo provável (ex: 3587)
        
    Returns:
        Lista de jogos (cada jogo é uma lista de strings com números) ou None se erro
    """
    arquivo = os.path.join(DIRETORIO_JOGOS_GERADOS, f"jogo_provavel_{id_jogo}.json")
    
    if not os.path.exists(arquivo):
        print(f"❌ Erro: Arquivo não encontrado: {arquivo}")
        return None
    
    try:
        with open(arquivo, 'r', encoding='utf-8') as f:
            jogos = json.load(f)
        
        if not isinstance(jogos, list):
            print(f"❌ Erro: Formato inválido. Esperado lista de jogos.")
            return None
        
        print(f"✅ Carregados {len(jogos)} jogos prováveis do arquivo {arquivo}")
        return jogos
    
    except (json.JSONDecodeError, IOError) as e:
        print(f"❌ Erro ao carregar arquivo: {e}")
        return None


def carregar_concurso(id_concurso: int) -> Optional[Dict]:
    """
    Carrega dados do concurso do arquivo JSON.
    
    Args:
        id_concurso: ID do concurso (ex: 3538)
        
    Returns:
        Dicionário com os dados do concurso ou None se erro
    """
    arquivo = os.path.join(DIRETORIO_DADOS, f"concurso_{id_concurso}.json")
    
    if not os.path.exists(arquivo):
        print(f"❌ Erro: Arquivo não encontrado: {arquivo}")
        return None
    
    try:
        with open(arquivo, 'r', encoding='utf-8') as f:
            concurso = json.load(f)
        
        if "dezenas" not in concurso:
            print(f"❌ Erro: Campo 'dezenas' não encontrado no arquivo do concurso.")
            return None
        
        print(f"✅ Carregado concurso {id_concurso} do arquivo {arquivo}")
        return concurso
    
    except (json.JSONDecodeError, IOError) as e:
        print(f"❌ Erro ao carregar arquivo: {e}")
        return None


def contar_acertos(jogo: List[str], dezenas_sorteadas: List[str]) -> int:
    """
    Conta quantos números do jogo estão nas dezenas sorteadas.
    
    Args:
        jogo: Lista de strings com os números do jogo
        dezenas_sorteadas: Lista de strings com as dezenas sorteadas
        
    Returns:
        Número de acertos
    """
    # Converter para sets para comparação mais eficiente
    jogo_set = set(jogo)
    dezenas_set = set(dezenas_sorteadas)
    
    # Intersecção dos conjuntos = números que estão em ambos
    acertos = len(jogo_set & dezenas_set)
    
    return acertos


def validar_jogos(id_jogo: int, id_concurso: int) -> None:
    """
    Função principal que valida todos os jogos prováveis comparando com o concurso.
    
    Args:
        id_jogo: ID do jogo provável
        id_concurso: ID do concurso
    """
    print("=" * 70)
    print(f"VALIDAÇÃO DE JOGOS PROVÁVEIS")
    print(f"Jogo provável: {id_jogo} | Concurso: {id_concurso}")
    print("=" * 70)
    print()
    
    # Carregar jogos prováveis
    jogos = carregar_jogos_provaveis(id_jogo)
    if jogos is None:
        return
    
    # Carregar concurso
    concurso = carregar_concurso(id_concurso)
    if concurso is None:
        return
    
    # Extrair dezenas sorteadas
    dezenas_sorteadas = concurso.get("dezenas", [])
    
    if not dezenas_sorteadas:
        print("❌ Erro: Nenhuma dezena encontrada no concurso.")
        return
    
    print(f"📊 Dezenas sorteadas no concurso {id_concurso}: {', '.join(dezenas_sorteadas)}")
    print()
    
    # Validar cada jogo
    resultados = []
    acertos_por_jogo = []
    
    for idx, jogo in enumerate(jogos, 1):
        num_acertos = contar_acertos(jogo, dezenas_sorteadas)
        acertos_por_jogo.append(num_acertos)
        resultados.append({
            "jogo": idx,
            "numeros": jogo,
            "acertos": num_acertos
        })
    
    # Calcular estatísticas
    total_jogos = len(jogos)
    max_acertos = max(acertos_por_jogo) if acertos_por_jogo else 0
    min_acertos = min(acertos_por_jogo) if acertos_por_jogo else 0
    media_acertos = sum(acertos_por_jogo) / total_jogos if total_jogos > 0 else 0
    
    # Distribuição de acertos
    distribuicao = Counter(acertos_por_jogo)
    
    # Exibir resultados
    print("=" * 70)
    print("RESULTADOS DA VALIDAÇÃO")
    print("=" * 70)
    print()
    print(f"📈 ESTATÍSTICAS:")
    print(f"   Total de jogos validados: {total_jogos:,}")
    print(f"   Máximo de acertos: {max_acertos}")
    print(f"   Mínimo de acertos: {min_acertos}")
    print(f"   Média de acertos: {media_acertos:.2f}")
    print()
    
    print(f"📊 DISTRIBUIÇÃO DE ACERTOS:")
    for num_acertos in sorted(distribuicao.keys(), reverse=True):
        quantidade = distribuicao[num_acertos]
        percentual = (quantidade / total_jogos) * 100
        barra = "█" * int(percentual / 2)  # Barra proporcional
        print(f"   {num_acertos:2d} acertos: {quantidade:6,} jogos ({percentual:5.2f}%) {barra}")
    print()
    
    # Exibir jogos com mais acertos (top 10)
    resultados_ordenados = sorted(resultados, key=lambda x: x["acertos"], reverse=True)
    top_acertos = resultados_ordenados[:10]
    
    if top_acertos and top_acertos[0]["acertos"] > 0:
        print("=" * 70)
        print(f"🏆 TOP 10 JOGOS COM MAIS ACERTOS:")
        print("=" * 70)
        for resultado in top_acertos:
            numeros_str = ", ".join(resultado["numeros"])
            print(f"   Jogo #{resultado['jogo']:6d}: {resultado['acertos']:2d} acertos | {numeros_str}")
        print()
    
    # Verificar se algum jogo teve 15 acertos (ganhador)
    jogos_ganhadores = [r for r in resultados if r["acertos"] == 15]
    if jogos_ganhadores:
        print("=" * 70)
        print("🎉 JOGOS GANHADORES (15 ACERTOS)!")
        print("=" * 70)
        for resultado in jogos_ganhadores:
            numeros_str = ", ".join(resultado["numeros"])
            print(f"   Jogo #{resultado['jogo']:6d}: {numeros_str}")
        print()
    else:
        print("ℹ️  Nenhum jogo teve 15 acertos (não houve ganhadores).")
        print()
    
    print("=" * 70)


def main():
    """Função principal que processa argumentos da linha de comando ou solicita input."""
    parser = argparse.ArgumentParser(
        description="Validador de Jogos Prováveis - Lotofácil",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:
  python validar_jogos_provaveis.py --j 3587 --c 3538
  python validar_jogos_provaveis.py --jogo 3584 --concurso 3585
        """
    )
    
    parser.add_argument(
        '--j',
        dest='id_jogo',
        type=int,
        help='ID do jogo provável (ex: 3587)'
    )
    
    parser.add_argument(
        '--jogo',
        dest='id_jogo',
        type=int,
        help='ID do jogo provável (ex: 3587)'
    )
    
    parser.add_argument(
        '--c',
        dest='id_concurso',
        type=int,
        help='ID do concurso (ex: 3538)'
    )
    
    parser.add_argument(
        '--concurso',
        dest='id_concurso',
        type=int,
        help='ID do concurso (ex: 3538)'
    )
    
    args = parser.parse_args()
    
    # Se os argumentos não foram fornecidos, solicitar input interativo
    if args.id_jogo is None or args.id_concurso is None:
        print("=" * 70)
        print("VALIDADOR DE JOGOS PROVÁVEIS - LOTOFÁCIL")
        print("=" * 70)
        print()
        
        try:
            if args.id_jogo is None:
                id_jogo = int(input("Digite o ID do jogo provável (ex: 3587): "))
            else:
                id_jogo = args.id_jogo
                
            if args.id_concurso is None:
                id_concurso = int(input("Digite o ID do concurso (ex: 3538): "))
            else:
                id_concurso = args.id_concurso
            print()
        except ValueError:
            print("❌ Erro: Os IDs devem ser números inteiros.")
            sys.exit(1)
        except KeyboardInterrupt:
            print("\n\n❌ Operação cancelada pelo usuário.")
            sys.exit(1)
    else:
        id_jogo = args.id_jogo
        id_concurso = args.id_concurso
    
    validar_jogos(id_jogo, id_concurso)


if __name__ == "__main__":
    main()
