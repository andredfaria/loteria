#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Análise de Combinações com Dezenas - Lotofácil
===============================================

Este script analisa quais outras dezenas aparecem mais frequentemente junto
com as dezenas fornecidas nos concursos históricos, e gera combinações baseadas
nas frequências encontradas.

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
import random
from typing import Dict, List, Optional, Tuple
from collections import defaultdict, Counter
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


def analisar_frequencias_junto(dezenas_fornecidas: List[int]) -> Tuple[Dict[int, int], int, List[Dict]]:
    """
    Analisa quais outras dezenas aparecem mais frequentemente junto com as dezenas fornecidas.
    
    Args:
        dezenas_fornecidas: Lista de dezenas fornecidas pelo usuário
        
    Returns:
        Tupla com (dicionário de frequências, total de concursos que contêm todas as dezenas, lista de concursos relevantes)
    """
    numeros_concursos = encontrar_arquivos_concursos()
    dezenas_fornecidas_set = set(dezenas_fornecidas)
    frequencias = defaultdict(int)
    concursos_relevantes = []
    total_concursos_com_todas = 0
    
    print(f"🔍 Analisando concursos que contêm as dezenas: {sorted(dezenas_fornecidas)}")
    print(f"📊 Processando {len(numeros_concursos)} concursos...\n")
    
    for i, numero_concurso in enumerate(numeros_concursos, 1):
        concurso = carregar_concurso(numero_concurso)
        
        if not concurso:
            continue
        
        dezenas = extrair_dezenas(concurso)
        dezenas_set = set(dezenas)
        
        # Verificar se todas as dezenas fornecidas estão neste concurso
        if dezenas_fornecidas_set.issubset(dezenas_set):
            total_concursos_com_todas += 1
            concursos_relevantes.append({
                "concurso": numero_concurso,
                "data": concurso.get("data", "N/A"),
                "dezenas": sorted(dezenas)
            })
            
            # Contar frequência das outras dezenas (excluindo as fornecidas)
            outras_dezenas = dezenas_set - dezenas_fornecidas_set
            for dezena in outras_dezenas:
                frequencias[dezena] += 1
        
        # Progresso a cada 100 concursos
        if i % 100 == 0:
            print(f"  Processados: {i}/{len(numeros_concursos)} concursos", end="\r")
    
    print(f"\n✅ Análise concluída!\n")
    
    return dict(frequencias), total_concursos_com_todas, concursos_relevantes


def gerar_estatisticas(frequencias: Dict[int, int], total_concursos: int) -> Dict:
    """
    Gera estatísticas sobre as frequências encontradas.
    
    Args:
        frequencias: Dicionário com frequências de cada dezena
        total_concursos: Número total de concursos que contêm todas as dezenas fornecidas
        
    Returns:
        Dicionário com estatísticas
    """
    if not frequencias or total_concursos == 0:
        return {
            "total_concursos": total_concursos,
            "dezenas_ordenadas": [],
            "estatisticas_dezenas": {}
        }
    
    # Ordenar dezenas por frequência (decrescente)
    dezenas_ordenadas = sorted(frequencias.items(), key=lambda x: x[1], reverse=True)
    
    # Criar estatísticas detalhadas para cada dezena
    estatisticas_dezenas = {}
    for dezena, frequencia in dezenas_ordenadas:
        percentual = (frequencia / total_concursos) * 100
        estatisticas_dezenas[dezena] = {
            "frequencia": frequencia,
            "percentual": percentual
        }
    
    return {
        "total_concursos": total_concursos,
        "dezenas_ordenadas": dezenas_ordenadas,
        "estatisticas_dezenas": estatisticas_dezenas
    }


def gerar_combinacoes(dezenas_fornecidas: List[int], frequencias: Dict[int, int], 
                     n_dezenas: int, quantidade: int = 1) -> List[List[int]]:
    """
    Gera combinações de N dezenas incluindo as fornecidas, escolhendo as outras baseadas nas frequências.
    
    Args:
        dezenas_fornecidas: Lista de dezenas que devem estar na combinação
        frequencias: Dicionário com frequências de cada dezena
        n_dezenas: Número total de dezenas na combinação
        quantidade: Quantidade de combinações a gerar
        
    Returns:
        Lista de combinações (cada combinação é uma lista de dezenas ordenadas)
    """
    dezenas_fornecidas_set = set(dezenas_fornecidas)
    num_fornecidas = len(dezenas_fornecidas)
    num_necessarias = n_dezenas - num_fornecidas
    
    if num_necessarias < 0:
        raise ValueError(f"Erro: Você forneceu {num_fornecidas} dezenas, mas pediu combinações de {n_dezenas} dezenas!")
    
    # Dezenas disponíveis (todas exceto as fornecidas)
    todas_dezenas = set(range(1, 26))
    dezenas_disponiveis = todas_dezenas - dezenas_fornecidas_set
    
    # Se não há frequências, usar seleção aleatória
    if not frequencias:
        print(f"⚠️  Aviso: Nenhuma frequência encontrada. Gerando combinações aleatórias.")
        combinacoes = []
        for _ in range(quantidade):
            outras_dezenas = sorted(random.sample(list(dezenas_disponiveis), num_necessarias))
            combinacao = sorted(dezenas_fornecidas + outras_dezenas)
            combinacoes.append(combinacao)
        return combinacoes
    
    # Ordenar dezenas disponíveis por frequência
    dezenas_ordenadas_por_freq = sorted(
        [(d, frequencias.get(d, 0)) for d in dezenas_disponiveis],
        key=lambda x: x[1],
        reverse=True
    )
    
    combinacoes = []
    
    for idx_combinacao in range(quantidade):
        if quantidade == 1:
            # Se apenas uma combinação, usar as mais frequentes
            outras_dezenas = [d for d, _ in dezenas_ordenadas_por_freq[:num_necessarias]]
        else:
            # Para múltiplas combinações, introduzir variação usando pesos baseados em frequência
            if idx_combinacao == 0:
                # Primeira combinação: usar as mais frequentes
                outras_dezenas = [d for d, _ in dezenas_ordenadas_por_freq[:num_necessarias]]
            else:
                # Outras combinações: usar seleção ponderada
                outras_dezenas = selecionar_dezenas_ponderadas(
                    dezenas_ordenadas_por_freq, num_necessarias, combinacoes
                )
        
        combinacao = sorted(dezenas_fornecidas + outras_dezenas)
        combinacoes.append(combinacao)
    
    return combinacoes


def selecionar_dezenas_ponderadas(dezenas_ordenadas: List[Tuple[int, int]], 
                                  num_necessarias: int, combinacoes_existentes: List[List[int]]) -> List[int]:
    """
    Seleciona dezenas usando pesos baseados em frequência, introduzindo variação.
    
    Args:
        dezenas_ordenadas: Lista de tuplas (dezena, frequencia) ordenada por frequência
        num_necessarias: Quantidade de dezenas a selecionar
        combinacoes_existentes: Combinações já geradas (para introduzir variação)
        
    Returns:
        Lista de dezenas selecionadas
    """
    # Criar pesos (frequência + 1 para evitar peso zero)
    # Introduzir pequena variação aleatória nos pesos para diversificar
    variacao = len(combinacoes_existentes) * 0.1
    pesos = [(d, f + 1 + random.uniform(0, variacao)) for d, f in dezenas_ordenadas]
    
    # Seleção ponderada
    dezenas_selecionadas = []
    pesos_disponiveis = pesos.copy()
    
    for _ in range(num_necessarias):
        if not pesos_disponiveis:
            break
        
        # Calcular probabilidades normalizadas
        total = sum(p for _, p in pesos_disponiveis)
        if total == 0:
            # Fallback para seleção aleatória
            escolhida = random.choice(pesos_disponiveis)[0]
        else:
            # Seleção ponderada
            r = random.uniform(0, total)
            acumulado = 0
            escolhida = None
            for d, p in pesos_disponiveis:
                acumulado += p
                if r <= acumulado:
                    escolhida = d
                    break
            
            if escolhida is None:
                escolhida = pesos_disponiveis[-1][0]
        
        dezenas_selecionadas.append(escolhida)
        # Remover a dezena selecionada
        pesos_disponiveis = [(d, p) for d, p in pesos_disponiveis if d != escolhida]
    
    return sorted(dezenas_selecionadas)


def imprimir_relatorio(dezenas_fornecidas: List[int], estatisticas: Dict, 
                      combinacoes: List[List[int]], top_n: int = 20):
    """
    Imprime o relatório completo com estatísticas e combinações geradas.
    
    Args:
        dezenas_fornecidas: Lista de dezenas fornecidas
        estatisticas: Dicionário com estatísticas
        combinacoes: Lista de combinações geradas
        top_n: Quantas dezenas mostrar no top
    """
    print("=" * 80)
    print("ANÁLISE DE COMBINAÇÕES COM DEZENAS - LOTOFÁCIL")
    print("=" * 80)
    print(f"\n📋 Dezenas fornecidas: {', '.join(f'{d:02d}' for d in sorted(dezenas_fornecidas))}")
    print(f"📊 Total de concursos analisados: {estatisticas['total_concursos']}")
    print()
    
    if estatisticas['total_concursos'] == 0:
        print("❌ Nenhum concurso encontrado contendo todas as dezenas fornecidas!")
        print("   Verifique se as dezenas estão corretas.")
        return
    
    # Estatísticas das dezenas
    print("📈 TOP DEZENAS QUE MAIS APARECEM JUNTO")
    print("-" * 80)
    print(f"{'Pos':<5} {'Dezena':<10} {'Frequência':<15} {'Percentual':<15}")
    print("-" * 80)
    
    dezenas_ordenadas = estatisticas['dezenas_ordenadas']
    estatisticas_dezenas = estatisticas['estatisticas_dezenas']
    
    for pos, (dezena, frequencia) in enumerate(dezenas_ordenadas[:top_n], 1):
        stats = estatisticas_dezenas[dezena]
        percentual = stats['percentual']
        print(f"{pos:<5} {dezena:02d}{'':<7} {frequencia:<15} {percentual:>13.2f}%")
    print()
    
    # Se há mais dezenas além do top_n, mostrar resumo
    if len(dezenas_ordenadas) > top_n:
        print(f"... e mais {len(dezenas_ordenadas) - top_n} dezenas")
        print()
    
    # Combinações geradas
    print("🎲 COMBINAÇÕES GERADAS")
    print("-" * 80)
    for idx, combinacao in enumerate(combinacoes, 1):
        dezenas_str = ", ".join(f"{d:02d}" for d in combinacao)
        print(f"Combinação {idx}: {dezenas_str}")
    print()
    
    # Informações adicionais sobre as combinações
    if len(combinacoes) > 0:
        primeira_combinacao = combinacoes[0]
        dezenas_adicionais = sorted([d for d in primeira_combinacao if d not in dezenas_fornecidas])
        print(f"📌 Dezenas adicionadas (baseadas nas frequências): {', '.join(f'{d:02d}' for d in dezenas_adicionais)}")
        print()


def parse_dezenas(dezenas_str: str) -> List[int]:
    """
    Converte string de dezenas separadas por vírgula em lista de inteiros.
    
    Args:
        dezenas_str: String com dezenas separadas por vírgula (ex: "01,05,10" ou "1,5,10")
        
    Returns:
        Lista de inteiros
    """
    dezenas = []
    for d in dezenas_str.split(','):
        d = d.strip()
        try:
            numero = int(d)
            if 1 <= numero <= 25:
                dezenas.append(numero)
            else:
                raise ValueError(f"Dezena {numero} está fora do intervalo válido (1-25)")
        except ValueError as e:
            raise ValueError(f"Erro ao processar dezena '{d}': {e}")
    
    if len(set(dezenas)) != len(dezenas):
        raise ValueError("Erro: Dezenas duplicadas encontradas!")
    
    return sorted(dezenas)


def main():
    """Função principal"""
    parser = argparse.ArgumentParser(
        description="Analisa combinações de dezenas da Lotofácil",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:
  # Analisar com dezenas 01, 05, 10 e gerar 1 combinação de 15 dezenas
  python3 analisar_combinacoes_dezenas.py --dezenas 01,05,10 --total 15 --quantidade 1
  
  # Analisar com múltiplas dezenas e gerar 5 combinações
  python3 analisar_combinacoes_dezenas.py -d 1,5,10,15 -n 15 -q 5 -t 25
        """
    )
    
    parser.add_argument(
        '--dezenas', '-d',
        type=str,
        required=True,
        help='Dezenas fornecidas separadas por vírgula (ex: 01,05,10 ou 1,5,10)'
    )
    
    parser.add_argument(
        '--total', '-n',
        type=int,
        default=15,
        help='Número total de dezenas na combinação (padrão: 15)'
    )
    
    parser.add_argument(
        '--quantidade', '-q',
        type=int,
        default=1,
        help='Quantidade de combinações a gerar (padrão: 1)'
    )
    
    parser.add_argument(
        '--top', '-t',
        type=int,
        default=20,
        help='Quantas dezenas mais frequentes mostrar no relatório (padrão: 20)'
    )
    
    args = parser.parse_args()
    
    # Validar argumentos
    if args.total < 1 or args.total > 25:
        print("❌ Erro: O número total de dezenas deve estar entre 1 e 25!", file=sys.stderr)
        sys.exit(1)
    
    if args.quantidade < 1:
        print("❌ Erro: A quantidade de combinações deve ser pelo menos 1!", file=sys.stderr)
        sys.exit(1)
    
    # Verificar se o diretório existe
    if not os.path.exists(DIRETORIO_DADOS):
        print(f"❌ Diretório '{DIRETORIO_DADOS}' não encontrado!", file=sys.stderr)
        sys.exit(1)
    
    try:
        # Parse das dezenas
        dezenas_fornecidas = parse_dezenas(args.dezenas)
        
        if len(dezenas_fornecidas) >= args.total:
            print(f"❌ Erro: Você forneceu {len(dezenas_fornecidas)} dezenas, mas pediu combinações de {args.total} dezenas!", file=sys.stderr)
            sys.exit(1)
        
        # Analisar frequências
        frequencias, total_concursos, concursos_relevantes = analisar_frequencias_junto(dezenas_fornecidas)
        
        # Gerar estatísticas
        estatisticas = gerar_estatisticas(frequencias, total_concursos)
        
        # Gerar combinações
        combinacoes = gerar_combinacoes(dezenas_fornecidas, frequencias, args.total, args.quantidade)
        
        # Imprimir relatório
        imprimir_relatorio(dezenas_fornecidas, estatisticas, combinacoes, args.top)
        
    except ValueError as e:
        print(f"❌ Erro: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Erro inesperado: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
