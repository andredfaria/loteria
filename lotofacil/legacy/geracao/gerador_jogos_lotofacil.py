#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gerador de Jogos Sugeridos para Lotofácil
==========================================

Este script analisa dados históricos da Lotofácil e gera 10 jogos sugeridos
baseados em critérios estatísticos descritos no relatório técnico.

IMPORTANTE: Este é um script de análise estatística e simulação. Os jogos
gerados são apenas sugestões baseadas em padrões históricos observados.
NÃO há garantia de ganho. Cada sorteio é um evento aleatório independente.

Autor: Baseado no Relatório Técnico: Estratégias Racionais para a Lotofácil
"""

import json
import os
import random
import uuid
import argparse
from typing import List, Dict, Tuple, Set
from collections import Counter
from pathlib import Path
from datetime import datetime


# ============================================================================
# 0. INTEGRAÇÃO COM ML
# ============================================================================

import sys
from pathlib import Path as PathML

ML_DISPONIVEL = None

def _check_ml_disponivel():
    global ML_DISPONIVEL, ML_Draw, ML_FrequencyEnsembleModel
    if ML_DISPONIVEL is not None:
        return ML_DISPONIVEL
    
    # Tentar imports direta do path do projeto
    try:
        from lotofacil_ml.models.frequency_ensemble import FrequencyEnsembleModel as ML_FrequencyEnsembleModel
        from lotofacil_ml.data.loader import Draw as ML_Draw
        ML_DISPONIVEL = True
        return True
    except ImportError:
        pass
    
    # Tentar com path absoluto
    try:
        sys.path.insert(0, '/home/andre/Documentos/projetos/loteria/lotofacil/src')
        from lotofacil_ml.models.frequency_ensemble import FrequencyEnsembleModel as ML_FrequencyEnsembleModel
        from lotofacil_ml.data.loader import Draw as ML_Draw
        ML_DISPONIVEL = True
        return True
    except ImportError as e:
        print(f"  ML import error: {e}")
        ML_DISPONIVEL = False
        return False


ML_Draw = None
ML_FrequencyEnsembleModel = None


def carregar_config_ml(caminho_json: str) -> Dict:
    """
    Carrega configuração de parâmetros gerada pelo módulo ML.
    
    Args:
        caminho_json: Caminho para arquivo JSON de recomendação
        
    Returns:
        Dicionário com parâmetros recomendados ou None se houver erro
    """
    try:
        with open(caminho_json, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        if 'params' not in config:
            print(f"⚠️  Arquivo ML não contém seção 'params': {caminho_json}")
            return None
        
        print(f"✓ Configuração ML carregada de: {caminho_json}")
        print(f"  Concurso target: {config.get('concurso_target', 'N/A')}")
        print(f"  Score esperado: {config.get('expected_score', {}).get('mean_hits', 'N/A'):.3f} acertos")
        
        return config['params']
    
    except FileNotFoundError:
        print(f"❌ ERRO: Arquivo ML não encontrado: {caminho_json}")
        return None
    except json.JSONDecodeError:
        print(f"❌ ERRO: Erro ao decodificar JSON: {caminho_json}")
        return None
    except Exception as e:
        print(f"❌ ERRO ao carregar config ML: {e}")
        return None


# ============================================================================
# 1. CARREGAMENTO E TRATAMENTO DE DADOS
# ============================================================================

def carregar_dados_historicos(caminho_arquivo: str = None,
                               concurso_limite: int = None) -> List[Dict]:
    """
    Carrega os dados históricos dos sorteios da Lotofácil.

    Args:
        caminho_arquivo: Caminho para o arquivo JSON com os dados históricos
        concurso_limite: Número do concurso de referência. Se informado, retorna apenas
                        concursos anteriores a este número. Se None, retorna todos os concursos.

    Returns:
        Lista de dicionários contendo os concursos com dezenas convertidas para inteiros

    Comentário: Os dados são ordenados por número de concurso para garantir
    ordem cronológica e facilitar análises temporais.
    """
    if caminho_arquivo is None:
        caminho_arquivo = str(Path(__file__).resolve().parent.parent.parent / "dados" / "numeros_sorteados.json")
    try:
        with open(caminho_arquivo, 'r', encoding='utf-8') as f:
            dados = json.load(f)
        
        # Converter strings de dezenas para inteiros e ordenar por concurso
        concursos_tratados = []
        for concurso in dados:
            dezenas_inteiros = [int(d) for d in concurso['dezenas']]
            concurso_tratado = {
                'concurso': concurso['concurso'],
                'data': concurso.get('data', ''),
                'dezenas': sorted(dezenas_inteiros)  # Garantir ordem crescente
            }
            concursos_tratados.append(concurso_tratado)
        
        # Ordenar por número de concurso (cronológico)
        concursos_tratados.sort(key=lambda x: x['concurso'])
        
        # Filtrar por concurso_limite se informado
        if concurso_limite is not None:
            concursos_tratados = [c for c in concursos_tratados if c['concurso'] < concurso_limite]
            print(f"✓ Dados carregados: {len(concursos_tratados)} concursos anteriores ao concurso {concurso_limite}")
        else:
            print(f"✓ Dados carregados: {len(concursos_tratados)} concursos")
        
        return concursos_tratados
    
    except FileNotFoundError:
        print(f"ERRO: Arquivo {caminho_arquivo} não encontrado!")
        return []
    except json.JSONDecodeError:
        print(f"ERRO: Erro ao decodificar JSON do arquivo {caminho_arquivo}")
        return []
    except Exception as e:
        print(f"ERRO ao carregar dados: {e}")
        return []


# ============================================================================
# 2. CÁLCULO DE ESTATÍSTICAS
# ============================================================================

def calcular_frequencia_numeros(concursos: List[Dict]) -> Dict[int, int]:
    """
    Calcula a frequência de aparição de cada número (1-25) nos sorteios históricos.
    
    Args:
        concursos: Lista de concursos com dezenas sorteadas
        
    Returns:
        Dicionário com número como chave e quantidade de vezes sorteado como valor
        
    Comentário: Números mais frequentes historicamente podem ser priorizados
    na geração de jogos, conforme mencionado no relatório técnico.
    """
    frequencia = Counter()
    for concurso in concursos:
        for dezena in concurso['dezenas']:
            frequencia[dezena] += 1
    
    return dict(frequencia)


def calcular_distribuicao_pares_impares(concursos: List[Dict]) -> Dict[Tuple[int, int], int]:
    """
    Analisa a distribuição histórica de números pares e ímpares nos sorteios.
    
    Args:
        concursos: Lista de concursos com dezenas sorteadas
        
    Returns:
        Dicionário com tupla (pares, ímpares) como chave e frequência como valor
        
    Comentário: Segundo o relatório técnico, as combinações mais comuns são:
    - 7 pares e 8 ímpares (31,26%)
    - 8 pares e 7 ímpares (25,29%)
    - 6 pares e 9 ímpares (20,49%)
    - 9 pares e 6 ímpares (11,64%)
    Essas 4 distribuições representam cerca de 88% dos sorteios.
    """
    distribuicao = Counter()
    for concurso in concursos:
        pares = sum(1 for d in concurso['dezenas'] if d % 2 == 0)
        impares = 15 - pares
        distribuicao[(pares, impares)] += 1
    
    return dict(distribuicao)


def calcular_distribuicao_somas(concursos: List[Dict]) -> Dict[str, int]:
    """
    Calcula a distribuição das somas dos 15 números sorteados em cada concurso.
    
    Args:
        concursos: Lista de concursos com dezenas sorteadas
        
    Returns:
        Dicionário com faixa de soma como chave e frequência como valor
        
    Comentário: Segundo o relatório técnico, 83,95% dos sorteios têm soma
    entre 171 e 220. Somas muito baixas ou muito altas são menos prováveis.
    """
    distribuicao = Counter()
    somas = []
    
    for concurso in concursos:
        soma = sum(concurso['dezenas'])
        somas.append(soma)
        
        # Classificar em faixas conforme relatório técnico
        if soma < 150:
            faixa = "< 150"
        elif 150 <= soma < 171:
            faixa = "150-170"
        elif 171 <= soma <= 220:
            faixa = "171-220"  # Faixa mais comum (83,95%)
        elif 221 <= soma <= 240:
            faixa = "221-240"
        else:
            faixa = "> 240"
        
        distribuicao[faixa] += 1
    
    return {
        'distribuicao_faixas': dict(distribuicao),
        'somas': somas,
        'soma_min': min(somas),
        'soma_max': max(somas),
        'soma_media': sum(somas) / len(somas) if somas else 0
    }


def analisar_consecutivos(concursos: List[Dict]) -> Dict:
    """
    Analisa padrões de números consecutivos nos sorteios históricos.
    
    Args:
        concursos: Lista de concursos com dezenas sorteadas
        
    Returns:
        Dicionário com estatísticas sobre números consecutivos
        
    Comentário: É comum que sorteios apresentem sequências de 3-5 números
    consecutivos. Jogos sem nenhuma sequência consecutiva são estatisticamente
    menos prováveis.
    """
    total_consecutivos = 0
    sequencias_3 = 0
    sequencias_4 = 0
    sequencias_5_mais = 0
    
    for concurso in concursos:
        dezenas = sorted(concurso['dezenas'])
        consecutivos_neste_concurso = 0
        seq_atual = 1
        
        for i in range(1, len(dezenas)):
            if dezenas[i] == dezenas[i-1] + 1:
                seq_atual += 1
            else:
                if seq_atual >= 2:
                    consecutivos_neste_concurso += seq_atual - 1
                    if seq_atual == 3:
                        sequencias_3 += 1
                    elif seq_atual == 4:
                        sequencias_4 += 1
                    elif seq_atual >= 5:
                        sequencias_5_mais += 1
                seq_atual = 1
        
        # Verificar última sequência
        if seq_atual >= 2:
            consecutivos_neste_concurso += seq_atual - 1
            if seq_atual == 3:
                sequencias_3 += 1
            elif seq_atual == 4:
                sequencias_4 += 1
            elif seq_atual >= 5:
                sequencias_5_mais += 1
        
        total_consecutivos += consecutivos_neste_concurso
    
    return {
        'total_concursos': len(concursos),
        'sequencias_3': sequencias_3,
        'sequencias_4': sequencias_4,
        'sequencias_5_mais': sequencias_5_mais,
        'media_consecutivos_por_concurso': total_consecutivos / len(concursos) if concursos else 0
    }


# ============================================================================
# 3. DEFINIÇÃO DE FILTROS E CRITÉRIOS
# ============================================================================

def contar_pares_impares(jogo: List[int]) -> Tuple[int, int]:
    """Retorna a quantidade de pares e ímpares em um jogo."""
    pares = sum(1 for n in jogo if n % 2 == 0)
    impares = len(jogo) - pares
    return (pares, impares)


def calcular_soma(jogo: List[int]) -> int:
    """Retorna a soma dos números de um jogo."""
    return sum(jogo)


def contar_moldura_miolo(jogo: List[int]) -> Tuple[int, int]:
    """
    Conta números da moldura (bordas: 1-5, 21-25) e do miolo (6-20).
    
    Comentário: Segundo o relatório técnico, a maioria dos sorteios tem
    entre 8 e 11 números da moldura e o restante no miolo. Jogos com todos
    os números na moldura ou todos no miolo são menos prováveis.
    """
    moldura = sum(1 for n in jogo if n <= 5 or n >= 21)
    miolo = len(jogo) - moldura
    return (moldura, miolo)


def contar_primos(jogo: List[int]) -> int:
    """
    Conta quantos números primos existem no jogo.
    
    Comentário: Os primos possíveis na Lotofácil são: 2, 3, 5, 7, 11, 13, 17, 19, 23.
    Segundo o relatório técnico, é comum ter entre 4-7 números primos.
    """
    primos = {2, 3, 5, 7, 11, 13, 17, 19, 23}
    return sum(1 for n in jogo if n in primos)


def contar_fibonacci(jogo: List[int]) -> int:
    """
    Conta quantos números da sequência de Fibonacci existem no jogo.
    
    Comentário: A sequência de Fibonacci até 25: 1, 2, 3, 5, 8, 13, 21.
    Segundo o relatório técnico, é comum ter entre 3-5 números desta sequência.
    """
    fibonacci = {1, 2, 3, 5, 8, 13, 21}
    return sum(1 for n in jogo if n in fibonacci)


def contar_por_faixa(jogo: List[int]) -> Dict[str, int]:
    """
    Conta quantos números do jogo caem em cada faixa de 5 números.
    """
    return {
        "faixa_1_5":   sum(1 for n in jogo if 1  <= n <= 5),
        "faixa_6_10":  sum(1 for n in jogo if 6  <= n <= 10),
        "faixa_11_15": sum(1 for n in jogo if 11 <= n <= 15),
        "faixa_16_20": sum(1 for n in jogo if 16 <= n <= 20),
        "faixa_21_25": sum(1 for n in jogo if 21 <= n <= 25),
    }


def ajustar_faixas_jogo(jogo: List[int], frequencia_numeros: Dict[int, int]) -> List[int]:
    """
    Pós-geração: se alguma faixa tiver 0 números, troca 1 número de uma
    faixa com >=4 (super-representada) pelo número mais frequente da faixa vazia.
    Tenta preservar soma 171-220.
    """
    FAIXAS = {
        "faixa_1_5":   list(range(1, 6)),
        "faixa_6_10":  list(range(6, 11)),
        "faixa_11_15": list(range(11, 16)),
        "faixa_16_20": list(range(16, 21)),
        "faixa_21_25": list(range(21, 26)),
    }

    jogo_atual = list(jogo)
    max_tentativas = 5

    for _ in range(max_tentativas):
        fc = contar_por_faixa(jogo_atual)
        faixas_vazias = [nome for nome, cnt in fc.items() if cnt == 0]
        faixas_cheias = [nome for nome, cnt in fc.items() if cnt >= 4]

        if not faixas_vazias:
            break
        if not faixas_cheias:
            break

        faixa_vazia = faixas_vazias[0]
        faixa_cheia = faixas_cheias[0]

        # Candidato na faixa vazia: mais frequente não presente no jogo
        nums_vazia = FAIXAS[faixa_vazia]
        candidato_entrar = max(
            [n for n in nums_vazia if n not in jogo_atual],
            key=lambda n: frequencia_numeros.get(n, 0),
            default=None
        )
        if candidato_entrar is None:
            break

        # Candidato a sair na faixa cheia: menos frequente presente no jogo
        nums_cheia = FAIXAS[faixa_cheia]
        candidato_sair = min(
            [n for n in nums_cheia if n in jogo_atual],
            key=lambda n: frequencia_numeros.get(n, 0),
            default=None
        )
        if candidato_sair is None:
            break

        # Verificar se a troca não quebra a faixa de soma
        novo_jogo = [n for n in jogo_atual if n != candidato_sair] + [candidato_entrar]
        nova_soma = sum(novo_jogo)
        if 171 <= nova_soma <= 220:
            jogo_atual = sorted(novo_jogo)
        else:
            break  # Não trocar se quebraria a soma

    return sorted(jogo_atual)


def contar_repetidos_do_ultimo(jogo: List[int], ultimo_concurso: List[int]) -> int:
    """
    Conta quantos números do jogo foram sorteados no último concurso.

    Comentário: Segundo o relatório técnico, é muito comum escolher entre
    8-10 números que foram sorteados no concurso anterior.
    """
    return sum(1 for n in jogo if n in ultimo_concurso)


def tem_consecutivos(jogo: List[int], min_sequencia: int = 2) -> bool:
    """
    Verifica se o jogo tem pelo menos uma sequência de números consecutivos.
    
    Args:
        jogo: Lista de números do jogo (deve estar ordenada)
        min_sequencia: Tamanho mínimo da sequência consecutiva
        
    Comentário: Jogos sem nenhuma sequência consecutiva são estatisticamente
    menos prováveis. Buscamos ter pelo menos uma sequência de 2 ou mais números.
    """
    jogo_ordenado = sorted(jogo)
    seq_atual = 1
    
    for i in range(1, len(jogo_ordenado)):
        if jogo_ordenado[i] == jogo_ordenado[i-1] + 1:
            seq_atual += 1
            if seq_atual >= min_sequencia:
                return True
        else:
            seq_atual = 1
    
    return seq_atual >= min_sequencia


def validar_combinacao(jogo: List[int], ultimo_concurso: List[int], estatisticas: Dict) -> Tuple[bool, List[str]]:
    """
    Valida se uma combinação atende aos critérios estatísticos.
    
    Args:
        jogo: Lista de 15 números do jogo
        ultimo_concurso: Dezenas do último concurso
        estatisticas: Dicionário com estatísticas históricas
        
    Returns:
        Tupla (é_valido, lista_de_mensagens)
        
    Comentário: Esta função verifica se o jogo respeita os padrões históricos
    identificados no relatório técnico. Não rejeita jogos que não atendam
    completamente, mas fornece feedback sobre quais critérios foram atendidos.
    """
    mensagens = []
    
    # Validar tamanho
    if len(jogo) != 15:
        return (False, ["Jogo deve ter exatamente 15 números"])
    
    # Validar intervalo
    if not all(1 <= n <= 25 for n in jogo):
        return (False, ["Todos os números devem estar entre 1 e 25"])
    
    # Validar duplicatas
    if len(set(jogo)) != 15:
        return (False, ["Não podem haver números repetidos"])
    
    # Validar pares/ímpares (padrão mais comum: 7-8 ou 8-7)
    pares, impares = contar_pares_impares(jogo)
    if (pares, impares) in [(7, 8), (8, 7), (6, 9), (9, 6)]:
        mensagens.append(f"✓ Pares/Ímpares: {pares}-{impares} (padrão comum)")
    else:
        mensagens.append(f"⚠ Pares/Ímpares: {pares}-{impares} (fora do padrão mais comum)")
    
    # Validar soma (faixa ideal: 171-220)
    soma = calcular_soma(jogo)
    if 171 <= soma <= 220:
        mensagens.append(f"✓ Soma: {soma} (faixa ideal: 171-220)")
    elif 150 <= soma < 171 or 221 <= soma <= 240:
        mensagens.append(f"⚠ Soma: {soma} (fora da faixa ideal, mas aceitável)")
    else:
        mensagens.append(f"⚠ Soma: {soma} (fora das faixas mais comuns)")
    
    # Validar moldura/miolo (ideal: 8-11 da moldura)
    moldura, miolo = contar_moldura_miolo(jogo)
    if 8 <= moldura <= 11:
        mensagens.append(f"✓ Moldura/Miolo: {moldura}-{miolo} (padrão ideal)")
    else:
        mensagens.append(f"⚠ Moldura/Miolo: {moldura}-{miolo} (fora do padrão ideal)")
    
    # Validar primos (ideal: 4-7)
    primos = contar_primos(jogo)
    if 4 <= primos <= 7:
        mensagens.append(f"✓ Primos: {primos} (padrão ideal: 4-7)")
    else:
        mensagens.append(f"⚠ Primos: {primos} (fora do padrão ideal: 4-7)")
    
    # Validar Fibonacci (ideal: 3-5)
    fib = contar_fibonacci(jogo)
    if 3 <= fib <= 5:
        mensagens.append(f"✓ Fibonacci: {fib} (padrão ideal: 3-5)")
    else:
        mensagens.append(f"⚠ Fibonacci: {fib} (fora do padrão ideal: 3-5)")
    
    # Validar repetição do último concurso (ideal: 8-10)
    repetidos = contar_repetidos_do_ultimo(jogo, ultimo_concurso)
    if 8 <= repetidos <= 10:
        mensagens.append(f"✓ Repetidos do último: {repetidos} (padrão ideal: 8-10)")
    else:
        mensagens.append(f"⚠ Repetidos do último: {repetidos} (fora do padrão ideal: 8-10)")
    
    # Validar consecutivos
    if tem_consecutivos(jogo, min_sequencia=2):
        mensagens.append("✓ Tem sequências consecutivas")
    else:
        mensagens.append("⚠ Sem sequências consecutivas (menos comum)")
    
    return (True, mensagens)


# ============================================================================
# 4. GERAÇÃO DE JOGOS
# ============================================================================

def calcular_numeros_ausentes_ciclo(concursos: List[Dict], num_concursos: int = 4) -> Set[int]:
    """
    Calcula quais números não apareceram nos últimos N concursos (ciclo das dezenas).
    
    Args:
        concursos: Lista de concursos históricos (ordenados por número de concurso)
        num_concursos: Quantidade de concursos para analisar (padrão: 4)
        
    Returns:
        Conjunto de números que não apareceram no período analisado
        
    Comentário: Segundo a hierarquia de estratégias, o ciclo das dezenas é a
    PRIMEIRA estratégia a ser aplicada. Identifica números "atrasados" que têm
    maior probabilidade de aparecer nos próximos sorteios.
    """
    if len(concursos) < num_concursos:
        num_concursos = len(concursos)
    
    # Pegar últimos N concursos
    ultimos_concursos = concursos[-num_concursos:]
    
    # Coletar todos os números que apareceram
    numeros_que_apareceram = set()
    for concurso in ultimos_concursos:
        numeros_que_apareceram.update(concurso['dezenas'])
    
    # Retornar números que não apareceram (1-25)
    todos_numeros = set(range(1, 26))
    numeros_ausentes = todos_numeros - numeros_que_apareceram
    
    return numeros_ausentes


def ajustar_soma_jogo(jogo: List[int], soma_alvo_min: int = 171, soma_alvo_max: int = 220) -> List[int]:
    """
    Ajusta o jogo para que a soma esteja na faixa ideal (Nível 1 - Altíssimo Impacto).
    
    Args:
        jogo: Lista de números do jogo (deve ter 15 números)
        soma_alvo_min: Soma mínima desejada (padrão: 171)
        soma_alvo_max: Soma máxima desejada (padrão: 220)
        
    Returns:
        Jogo ajustado com soma na faixa ideal
        
    Comentário: Esta é a estratégia de maior precedência (~84% de ocorrência).
    Prioriza garantir que a soma esteja entre 171-220 antes de qualquer outro critério.
    """
    if len(jogo) != 15:
        return jogo
    
    soma_atual = calcular_soma(jogo)
    
    # Se já está na faixa ideal, retornar como está
    if soma_alvo_min <= soma_atual <= soma_alvo_max:
        return sorted(jogo)
    
    jogo_copia = jogo.copy()
    numeros_disponiveis = list(set(range(1, 26)) - set(jogo_copia))
    
    # Se soma está muito baixa, substituir números baixos por números mais altos
    if soma_atual < soma_alvo_min:
        diferenca = soma_alvo_min - soma_atual
        # Ordenar números do jogo do menor para o maior
        # Ordenar números disponíveis do maior para o menor
        numeros_baixos = sorted([n for n in jogo_copia if n <= 12])
        numeros_altos_disponiveis = sorted([n for n in numeros_disponiveis if n >= 14], reverse=True)
        
        for num_baixo in numeros_baixos:
            if diferenca <= 0:
                break
            for num_alto in numeros_altos_disponiveis:
                ganho = num_alto - num_baixo
                if ganho > 0 and ganho <= diferenca + 10:
                    idx = jogo_copia.index(num_baixo)
                    jogo_copia[idx] = num_alto
                    numeros_altos_disponiveis.remove(num_alto)
                    soma_atual = calcular_soma(jogo_copia)
                    diferenca = soma_alvo_min - soma_atual
                    if soma_alvo_min <= soma_atual <= soma_alvo_max:
                        return sorted(jogo_copia)
                    break
    
    # Se soma está muito alta, substituir números altos por números mais baixos
    elif soma_atual > soma_alvo_max:
        diferenca = soma_atual - soma_alvo_max
        # Ordenar números do jogo do maior para o menor
        # Ordenar números disponíveis do menor para o maior
        numeros_altos = sorted([n for n in jogo_copia if n >= 14], reverse=True)
        numeros_baixos_disponiveis = sorted([n for n in numeros_disponiveis if n <= 12])
        
        for num_alto in numeros_altos:
            if diferenca <= 0:
                break
            for num_baixo in numeros_baixos_disponiveis:
                reducao = num_alto - num_baixo
                if reducao > 0 and reducao <= diferenca + 10:
                    idx = jogo_copia.index(num_alto)
                    jogo_copia[idx] = num_baixo
                    numeros_baixos_disponiveis.remove(num_baixo)
                    soma_atual = calcular_soma(jogo_copia)
                    diferenca = soma_atual - soma_alvo_max
                    if soma_alvo_min <= soma_atual <= soma_alvo_max:
                        return sorted(jogo_copia)
                    break
    
    return sorted(jogo_copia)


def gerar_combinacao_estatistica(ultimo_concurso: List[int], frequencia_numeros: Dict[int, int],
                                 concursos: List[Dict], variacao: int = 0) -> List[int]:
    """
    Gera uma combinação de 15 números seguindo a hierarquia de precedência das estratégias.
    
    Args:
        ultimo_concurso: Dezenas do último concurso (para repetição parcial)
        frequencia_numeros: Dicionário com frequência de cada número
        concursos: Lista de concursos históricos (para calcular ciclo das dezenas)
        variacao: Parâmetro para variar a estratégia de geração (0-9)
        
    Returns:
        Lista com 15 números ordenados
        
    Comentário: Esta função implementa a geração seguindo a hierarquia de precedência:
    
    PRIMEIRO: Ciclo das Dezenas - Números ausentes nos últimos 4 concursos (estratégia inicial)
    
    NÍVEL 1 (Altíssimo Impacto - >80%):
    - Soma das Dezenas: Entre 171 e 220 (~84%)
    
    NÍVEL 2 (Alto Impacto - 55-80%):
    - Números Repetidos: Entre 8 e 10 dezenas do último concurso (~70%)
    - Pares/Ímpares: 7-8 ou 8-7 (~56%)
    
    NÍVEL 3 (Médio Impacto):
    - Moldura: Entre 9 e 10 dezenas da moldura (~55%)
    
    A função aplica os filtros em cascata, começando pelo ciclo das dezenas,
    depois garantindo o Nível 1, depois Nível 2, e por fim refinando com Nível 3.
    """
    jogo = []
    numeros_disponiveis = set(range(1, 26))
    
    # ========================================================================
    # PRIMEIRO: CICLO DAS DEZENAS - Números ausentes nos últimos 4 concursos
    # ========================================================================
    # Esta é a primeira estratégia a ser aplicada conforme a hierarquia
    numeros_ausentes_ciclo = calcular_numeros_ausentes_ciclo(concursos, num_concursos=4)
    
    # Quantos números do ciclo ausente vamos priorizar (variar entre 5-10)
    # Priorizar números ausentes, mas não exclusivamente
    qtd_priorizar_ciclo = 5 + (variacao % 6)  # 5 a 10 números do ciclo
    
    # Selecionar números ausentes do ciclo para incluir no jogo
    numeros_ausentes_ordenados = sorted(numeros_ausentes_ciclo, 
                                       key=lambda x: frequencia_numeros.get(x, 0), 
                                       reverse=True)
    
    # Incluir números ausentes do ciclo (prioridade inicial)
    numeros_ciclo_selecionados = numeros_ausentes_ordenados[:min(qtd_priorizar_ciclo, len(numeros_ausentes_ordenados))]
    jogo.extend(numeros_ciclo_selecionados)
    numeros_usados = set(jogo)
    numeros_disponiveis -= numeros_usados
    
    # ========================================================================
    # NÍVEL 2: Números Repetidos do Concurso Anterior (8-10 dezenas, ~70%)
    # ========================================================================
    qtde_repetir = 8 + (variacao % 3)  # 8, 9 ou 10
    
    # Selecionar números do último concurso que ainda não estão no jogo
    ultimo_disponivel = [n for n in ultimo_concurso if n not in jogo]
    
    # Quantos números repetidos ainda podemos adicionar
    qtd_repetir_restante = min(qtde_repetir, len(ultimo_disponivel), 15 - len(jogo))
    
    if qtd_repetir_restante > 0:
        # Selecionar quais números repetir
        if variacao < 3:
            # Priorizar números mais frequentes do último concurso
            ultimo_ordenado_por_freq = sorted(ultimo_disponivel, 
                                            key=lambda x: frequencia_numeros.get(x, 0), 
                                            reverse=True)
            repetidos = ultimo_ordenado_por_freq[:qtd_repetir_restante]
        elif variacao < 6:
            # Seleção aleatória controlada
            repetidos = random.sample(ultimo_disponivel, qtd_repetir_restante)
        else:
            # Priorizar números menos frequentes do último (diversificação)
            ultimo_ordenado_por_freq = sorted(ultimo_disponivel, 
                                            key=lambda x: frequencia_numeros.get(x, 0))
            repetidos = ultimo_ordenado_por_freq[:qtd_repetir_restante]
        
        jogo.extend(repetidos)
        numeros_usados.update(repetidos)
        numeros_disponiveis -= set(repetidos)
    
    # ========================================================================
    # Preencher números restantes balanceando todos os critérios
    # ========================================================================
    numeros_faltando = 15 - len(jogo)
    
    # Criar pool de candidatos priorizando números ausentes do ciclo que ainda não foram usados
    candidatos = []
    numeros_ausentes_restantes = numeros_ausentes_ciclo - numeros_usados
    
    # Adicionar números ausentes do ciclo que ainda não estão no jogo (prioridade)
    if numeros_ausentes_restantes:
        ausentes_ordenados = sorted(numeros_ausentes_restantes, 
                                   key=lambda x: frequencia_numeros.get(x, 0), 
                                   reverse=True)
        candidatos.extend(ausentes_ordenados)
    
    # Adicionar outros números disponíveis ordenados por frequência
    numeros_por_frequencia = sorted(numeros_disponiveis, 
                                   key=lambda x: frequencia_numeros.get(x, 0), 
                                   reverse=True)
    candidatos.extend(numeros_por_frequencia)
    
    # Selecionar números restantes balanceando critérios
    for _ in range(numeros_faltando):
        melhor_numero = None
        melhor_score = -1
        
        for num in candidatos:
            if num in jogo:
                continue
            
            jogo_teste = jogo + [num]
            score = 0
            
            # BONUS MÁXIMO: Números ausentes do ciclo (estratégia inicial)
            if num in numeros_ausentes_restantes:
                score += 300  # Prioridade máxima para ciclo das dezenas
            
            # NÍVEL 1: Soma (171-220 é ideal, ~84%) - PESO MÁXIMO
            soma = calcular_soma(jogo_teste)
            if 171 <= soma <= 220:
                score += 200  # Prioridade máxima (Nível 1)
            elif 150 <= soma < 171 or 221 <= soma <= 240:
                score += 50
            elif 140 <= soma < 150 or 241 <= soma <= 250:
                score += 10
            
            # NÍVEL 2: Pares/Ímpares (7-8 ou 8-7 é ideal, ~56%)
            pares, impares = contar_pares_impares(jogo_teste)
            if (pares, impares) in [(7, 8), (8, 7)]:
                score += 100  # Prioridade alta (Nível 2)
            elif (pares, impares) in [(6, 9), (9, 6)]:
                score += 50
            
            # NÍVEL 2: Repetidos do último (8-10 é ideal, ~70%)
            repetidos_count = contar_repetidos_do_ultimo(jogo_teste, ultimo_concurso)
            if 8 <= repetidos_count <= 10:
                score += 80  # Prioridade alta (Nível 2)
            elif 7 <= repetidos_count <= 11:
                score += 40
            
            # NÍVEL 3: Moldura (9-10 é ideal, ~55%)
            moldura, miolo = contar_moldura_miolo(jogo_teste)
            if 9 <= moldura <= 10:
                score += 30
            elif 8 <= moldura <= 11:
                score += 15
            
            # Frequência histórica (peso menor que critérios hierárquicos)
            score += frequencia_numeros.get(num, 0) * 2
            
            # Consecutivos (bonus menor)
            if len(jogo_teste) == 15:
                if tem_consecutivos(jogo_teste):
                    score += 20

            # FAIXAS — penaliza faixas descobertas, bonifica cobertura total
            if len(jogo_teste) == 15:
                faixas_teste = contar_por_faixa(jogo_teste)
                faixas_cobertas = sum(1 for v in faixas_teste.values() if v >= 2)
                if faixas_cobertas == 5:
                    score += 60    # Todas as 5 faixas com >=2 números
                elif faixas_cobertas == 4:
                    score += 30
                elif faixas_cobertas <= 2:
                    score -= 40    # Penaliza fortemente ausência de 3+ faixas

            if score > melhor_score:
                melhor_score = score
                melhor_numero = num
        
        if melhor_numero:
            jogo.append(melhor_numero)
            if melhor_numero in candidatos:
                candidatos.remove(melhor_numero)
        else:
            # Fallback: pegar qualquer número disponível
            if candidatos:
                jogo.append(candidatos.pop(0))
            elif numeros_por_frequencia:
                jogo.append(numeros_por_frequencia.pop(0))
    
    # Garantir que temos exatamente 15 números
    jogo = jogo[:15]
    
    # ========================================================================
    # NÍVEL 1: AJUSTE FINO DA SOMA (Prioridade Absoluta)
    # ========================================================================
    # Garantir que a soma está na faixa ideal (171-220)
    jogo = ajustar_soma_jogo(jogo, soma_alvo_min=171, soma_alvo_max=220)
    
    # ========================================================================
    # NÍVEL 2: AJUSTE FINO DE PARES/ÍMPARES
    # ========================================================================
    # Se possível, ajustar para 7-8 ou 8-7 sem quebrar a soma
    pares, impares = contar_pares_impares(jogo)
    soma_atual = calcular_soma(jogo)
    
    if (pares, impares) not in [(7, 8), (8, 7)]:
        # Tentar ajustar trocando um par por ímpar ou vice-versa
        pares_no_jogo = [n for n in jogo if n % 2 == 0]
        impares_no_jogo = [n for n in jogo if n % 2 != 0]
        numeros_fora = list(set(range(1, 26)) - set(jogo))
        
        ajustado = False
        
        if pares > 8:  # Muitos pares, precisa de mais ímpares
            # Trocar um par por um ímpar
            for par in pares_no_jogo:
                if ajustado:
                    break
                for impar in numeros_fora:
                    if impar % 2 != 0:
                        jogo_novo = [n for n in jogo if n != par] + [impar]
                        soma_nova = calcular_soma(jogo_novo)
                        pares_novo, impares_novo = contar_pares_impares(jogo_novo)
                        if 171 <= soma_nova <= 220 and (pares_novo, impares_novo) in [(7, 8), (8, 7)]:
                            jogo = jogo_novo
                            ajustado = True
                            break
        elif pares < 7:  # Poucos pares, precisa de mais pares
            # Trocar um ímpar por um par
            for impar in impares_no_jogo:
                if ajustado:
                    break
                for par in numeros_fora:
                    if par % 2 == 0:
                        jogo_novo = [n for n in jogo if n != impar] + [par]
                        soma_nova = calcular_soma(jogo_novo)
                        pares_novo, impares_novo = contar_pares_impares(jogo_novo)
                        if 171 <= soma_nova <= 220 and (pares_novo, impares_novo) in [(7, 8), (8, 7)]:
                            jogo = jogo_novo
                            ajustado = True
                            break
    
    # Garantir que ainda temos 15 números únicos
    jogo = sorted(list(set(jogo))[:15])
    
    # Se faltar números, preencher com os mais frequentes disponíveis
    while len(jogo) < 15:
        numeros_faltando = set(range(1, 26)) - set(jogo)
        if numeros_faltando:
            num_mais_freq = max(numeros_faltando, key=lambda x: frequencia_numeros.get(x, 0))
            jogo.append(num_mais_freq)
        else:
            break
    
    jogo = sorted(jogo[:15])
    
    # Ajuste final da soma (garantir Nível 1)
    jogo = ajustar_soma_jogo(jogo, soma_alvo_min=171, soma_alvo_max=220)

    # Ajuste de faixas (pós-geração): corrigir faixas descobertas
    jogo = ajustar_faixas_jogo(jogo, frequencia_numeros)

    return sorted(jogo)


def gerar_jogos(concursos: List[Dict], estatisticas: Dict, quantidade: int = 10) -> List[List[int]]:
    """
    Gera jogos variados aplicando diferentes estratégias estatísticas.
    
    Args:
        concursos: Lista de concursos históricos
        estatisticas: Dicionário com todas as estatísticas calculadas
        quantidade: Quantidade de jogos a gerar (padrão: 10)
        
    Returns:
        Lista com jogos (cada jogo é uma lista de 15 números)
        
    Comentário: Cada jogo é gerado com uma variação diferente dos parâmetros
    para garantir diversidade nas combinações sugeridas.
    """
    if not concursos:
        return []
    
    ultimo_concurso = concursos[-1]['dezenas']
    frequencia_numeros = estatisticas['frequencia']
    
    jogos = []
    tentativas = 0
    max_tentativas = 50
    
    # Gerar jogos variados
    for variacao in range(quantidade):
        tentativa = 0
        jogo_valido = False
        
        while not jogo_valido and tentativa < max_tentativas:
            jogo = gerar_combinacao_estatistica(ultimo_concurso, frequencia_numeros, 
                                               concursos, variacao=variacao)
            
            # Validar se o jogo não foi gerado anteriormente
            if jogo not in jogos:
                jogos.append(jogo)
                jogo_valido = True
            else:
                tentativa += 1
                variacao += 1  # Mudar variação para gerar jogo diferente
        
        if not jogo_valido:
            # Fallback: gerar jogo completamente diferente
            jogo_base = ultimo_concurso.copy()
            numeros_disponiveis = [n for n in range(1, 26) if n not in jogo_base]
            
            # Remover alguns e adicionar outros
            numeros_remover = random.sample(jogo_base, 5)
            numeros_adicionar = random.sample(numeros_disponiveis, 5)
            
            jogo = [n for n in jogo_base if n not in numeros_remover] + numeros_adicionar
            jogo = sorted(jogo[:15])
            
            if jogo not in jogos:
                jogos.append(jogo)
    
    return jogos[:quantidade]  # Garantir que retorna exatamente a quantidade solicitada


# ============================================================================
# 4.1. GERAÇÃO HÍBRIDA ML (80%) + ESTATÍSTICA (20%)
# ============================================================================

def obter_probabilidades_ml(concursos: List[Dict], janela: int = 120) -> List[float]:
    """
    Obtém probabilidades do modelo ML usando janela de N concursos.
    
    Args:
        concursos: Lista de concursos históricos
        janela: Número de concursos para treinar o modelo (padrão: 120)
    
    Returns:
        Lista de 25 probabilidades (uma para cada número 1-25)
    """
    if not _check_ml_disponivel():
        print("⚠️  ML não disponível, usando frequências simples")
        freq = calcular_frequencia_numeros(concursos)
        total = sum(freq.values()) if freq else 1
        return [freq.get(i, 0) / total for i in range(1, 26)]
    
    if len(concursos) < 10:
        print(f"⚠️  Dados insuficientes ({len(concursos)} concursos), usando frequências simples")
        freq = calcular_frequencia_numeros(concursos)
        total = sum(freq.values())
        return [freq.get(i, 0) / total for i in range(1, 26)]
    
    ultimos = concursos[-janela:] if len(concursos) >= janela else concursos
    
    draws = [ML_Draw(concurso=c['concurso'], dezenas=c['dezenas'], data=c.get('data', '')) for c in ultimos]
    
    modelo = ML_FrequencyEnsembleModel(windows={janela: 1.0})
    modelo.fit(draws)
    
    probs = modelo.predict_proba()
    return probs.tolist()


def obter_probabilidades_estatistica(concursos: List[Dict], ultimo_concurso: List[int]) -> List[float]:
    """
    Calcula probabilidades baseadas no ÚLTIMO concurso (padrão de repetição).
    
    Args:
        concursos: Lista de concursos históricos
        ultimo_concurso: Dezenas do último concurso
    
    Returns:
        Lista de 25 probabilidades (uma para cada número 1-25)
    """
    freq = calcular_frequencia_numeros(concursos)
    max_freq = max(freq.values()) if freq else 1
    
    probs = []
    for num in range(1, 26):
        p_freq = freq.get(num, 0) / max_freq
        
        # Padrão do último concurso: 8-10 números se repetem (80% do jogo)
        # Quanto mais próximo de 8-10 repetições, maior a probabilidade
        repetido = 1.0 if num in ultimo_concurso else 0.1
        
        # Ciclo: números ausentes nos últimos 4 concursos têm maior chance
        ciclo = calcular_numeros_ausentes_ciclo(concursos, num_concursos=4)
        p_ciclo = 1.2 if num in ciclo else 0.8
        
        # 20% baseado nos padrões do último concurso (prioridade a repetidos)
        prob = (p_freq * 0.3) + (repetido * 0.5) + (p_ciclo * 0.2)
        probs.append(prob)
    
    total = sum(probs)
    return [p / total for p in probs]


def mesclar_probabilidades(probs_ml: List[float], probs_estat: List[float], peso_ml: float = 0.8) -> List[float]:
    """
    Mescla duas listas de probabilidades.
    
    Args:
        probs_ml: Probabilidades do modelo ML
        probs_estat: Probabilidades da estatística
        peso_ml: Peso do ML (0.8 = 80%)
    
    Returns:
        Lista de 25 probabilidades mescladas
    """
    peso_estat = 1.0 - peso_ml
    mescladas = []
    for i in range(25):
        p = (probs_ml[i] * peso_ml) + (probs_estat[i] * peso_estat)
        mescladas.append(p)
    
    total = sum(mescladas)
    return [p / total for p in mescladas]


def gerar_jogo_hibrido(probs_mescladas: List[float], ultimo_concurso: List[int], 
                       frequencia_numeros: Dict[int, int], concursos: List[Dict]) -> List[int]:
    """
    Gera um jogo baseado em probabilidades mescladas, com ajustes de validação.
    
    Args:
        probs_mescladas: Probabilidades combinadas (ML + estatística)
        ultimo_concurso: Dezenas do último concurso
        frequencia_numeros: Frequência histórica dos números
        concursos: Lista de concursos históricos
    
    Returns:
        Lista de 15 números ordenados
    """
    numeros_disponiveis = list(range(1, 26))
    
    indices_ordenados = sorted(range(25), key=lambda i: probs_mescladas[i], reverse=True)
    
    jogo = []
    for idx in indices_ordenados:
        if len(jogo) == 15:
            break
        num = idx + 1
        
        if num not in jogo:
            jogo.append(num)
    
    while len(jogo) < 15:
        for idx in indices_ordenados:
            num = idx + 1
            if num not in jogo:
                jogo.append(num)
                break
    
    jogo = ajustar_soma_jogo(jogo, soma_alvo_min=171, soma_alvo_max=220)
    
    pares, impares = contar_pares_impares(jogo)
    if (pares, impares) not in [(7, 8), (8, 7), (6, 9), (9, 6)]:
        jogo = ajustar_faixas_jogo(jogo, frequencia_numeros)
    
    return sorted(jogo)


def gerar_jogos_hibridos(concursos: List[Dict], estatisticas: Dict, 
                         peso_ml: float = 0.8, janela_ml: int = 120,
                         quantidade: int = 1) -> List[List[int]]:
    """
    Gera jogos usando combinação de ML (80%) + Estatística (20%).
    
    Args:
        concursos: Lista de concursos históricos
        estatisticas: Dicionário com estatísticas
        peso_ml: Peso do ML na mesclagem (padrão: 0.8 = 80%)
        janela_ml: Janela de concursos para o ML (padrão: 120)
        quantidade: Quantidade de jogos a gerar
    
    Returns:
        Lista de jogos (cada jogo é lista de 15 números)
    """
    if not concursos:
        return []
    
    ultimo_concurso = concursos[-1]['dezenas']
    frequencia_numeros = estatisticas['frequencia']
    
    print(f"\n🤖 Gerando jogos HÍBRIDOS (ML {peso_ml*100:.0f}% + Estatística {100-peso_ml*100:.0f}%)")
    print(f"   📊 ML: janela de {janela_ml} concursos")
    
    probs_ml = obter_probabilidades_ml(concursos, janela=janela_ml)
    probs_estat = obter_probabilidades_estatistica(concursos, ultimo_concurso)
    probs_mescladas = mesclar_probabilidades(probs_ml, probs_estat, peso_ml=peso_ml)
    
    print(f"   ✅ Probabilidades mescladas obtidas")
    
    jogos = []
    for i in range(quantidade):
        jogo = gerar_jogo_hibrido(probs_mescladas, ultimo_concurso, 
                                  frequencia_numeros, concursos)
        jogos.append(jogo)
    
    return jogos


# ============================================================================
# 5. APRESENTAÇÃO DOS RESULTADOS
# ============================================================================

def imprimir_estatisticas(estatisticas: Dict, concursos: List[Dict]):
    """
    Imprime um resumo das estatísticas históricas calculadas.
    
    Comentário: Esta função apresenta ao usuário os padrões identificados
    nos dados históricos, fornecendo contexto para os jogos gerados.
    """
    print("\n" + "="*70)
    print(" ESTATÍSTICAS HISTÓRICAS DA LOTOFÁCIL")
    print("="*70)
    
    # Frequência de números
    print("\n📊 NÚMEROS MAIS FREQUENTES (Top 10):")
    freq = estatisticas['frequencia']
    numeros_ordenados = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    for i, (num, count) in enumerate(numeros_ordenados[:10], 1):
        print(f"   {i:2d}. Número {num:2d}: {count:4d} vezes ({count/len(concursos)*100:.1f}%)")
    
    # Distribuição pares/ímpares
    print("\n📊 DISTRIBUIÇÃO PARES/ÍMPARES:")
    dist_pi = estatisticas['pares_impares']
    pares_impares_ordenados = sorted(dist_pi.items(), key=lambda x: x[1], reverse=True)
    total = len(concursos)
    for (pares, impares), count in pares_impares_ordenados[:5]:
        porcentagem = count / total * 100
        print(f"   {pares} pares / {impares} ímpares: {count:4d} concursos ({porcentagem:.2f}%)")
    
    # Distribuição de somas
    print("\n📊 DISTRIBUIÇÃO DE SOMAS:")
    dist_somas = estatisticas['somas']
    print(f"   Soma mínima: {dist_somas['soma_min']}")
    print(f"   Soma máxima: {dist_somas['soma_max']}")
    print(f"   Soma média:  {dist_somas['soma_media']:.1f}")
    print("\n   Faixas de soma:")
    for faixa, count in sorted(dist_somas['distribuicao_faixas'].items(), 
                              key=lambda x: x[1], reverse=True):
        porcentagem = count / total * 100
        print(f"   {faixa:10s}: {count:4d} concursos ({porcentagem:.2f}%)")
    
    # Consecutivos
    print("\n📊 NÚMEROS CONSECUTIVOS:")
    consec = estatisticas['consecutivos']
    print(f"   Sequências de 3 números: {consec['sequencias_3']} ocorrências")
    print(f"   Sequências de 4 números: {consec['sequencias_4']} ocorrências")
    print(f"   Sequências de 5+ números: {consec['sequencias_5_mais']} ocorrências")
    print(f"   Média de consecutivos por concurso: {consec['media_consecutivos_por_concurso']:.2f}")


def imprimir_jogos(jogos: List[List[int]], ultimo_concurso: List[int], estatisticas: Dict):
    """
    Imprime os jogos gerados com suas validações.
    
    Comentário: Cada jogo é apresentado com suas características estatísticas
    para que o usuário possa entender o raciocínio por trás de cada sugestão.
    """
    # print("\n" + "="*70)
    # print(" JOGOS SUGERIDOS PARA O PRÓXIMO SORTEIO")
    # print("="*70)
    # print("\n⚠️  AVISO IMPORTANTE:")
    # print("   Estes são jogos SUGERIDOS baseados em análise estatística de dados históricos.")
    # print("   NÃO há garantia de ganho. Cada sorteio é um evento aleatório independente.")
    # print("   Use estas sugestões como ferramenta de apoio, não como promessa de lucro.\n")
    
    for i, jogo in enumerate(jogos, 1):
        print(f"\n{'─'*70}")
        print(f"JOGO {i:2d}: {', '.join(f'{n:02d}' for n in jogo)}")
        print(f"{'─'*70}")
        
        # Validação e características
        valido, mensagens = validar_combinacao(jogo, ultimo_concurso, estatisticas)
        
        # Características principais
        pares, impares = contar_pares_impares(jogo)
        soma = calcular_soma(jogo)
        moldura, miolo = contar_moldura_miolo(jogo)
        primos = contar_primos(jogo)
        fib = contar_fibonacci(jogo)
        repetidos = contar_repetidos_do_ultimo(jogo, ultimo_concurso)
        
        # print(f"   Pares/Ímpares: {pares}-{impares} | Soma: {soma} | "
        #       f"Moldura/Miolo: {moldura}-{miolo}")
        # print(f"   Primos: {primos} | Fibonacci: {fib} | "
        #       f"Repetidos do último concurso: {repetidos}/15")
        
        # Sequências consecutivas
        jogo_ordenado = sorted(jogo)
        sequencias = []
        seq_atual = [jogo_ordenado[0]]
        for j in range(1, len(jogo_ordenado)):
            if jogo_ordenado[j] == jogo_ordenado[j-1] + 1:
                seq_atual.append(jogo_ordenado[j])
            else:
                if len(seq_atual) >= 2:
                    sequencias.append(seq_atual)
                seq_atual = [jogo_ordenado[j]]
        if len(seq_atual) >= 2:
            sequencias.append(seq_atual)
        
        if sequencias:
            seq_str = " | ".join([f"{min(s)}-{max(s)}" if len(s) > 2 else f"{s[0]},{s[1]}" 
                                 for s in sequencias])
            # print(f"   Sequências consecutivas: {seq_str}")


# ============================================================================
# 6. SALVAMENTO EM ARQUIVO
# ============================================================================

def gerar_conteudo_markdown(jogos: List[List[int]], ultimo_concurso: List[int], 
                            estatisticas: Dict, concursos: List[Dict]) -> str:
    """
    Gera o conteúdo do arquivo em formato JSON com array de jogos.
    
    Args:
        jogos: Lista com os jogos gerados
        ultimo_concurso: Dezenas do último concurso (não usado, mantido para compatibilidade)
        estatisticas: Dicionário com todas as estatísticas calculadas (não usado, mantido para compatibilidade)
        concursos: Lista de concursos históricos (não usado, mantido para compatibilidade)
        
    Returns:
        String JSON com array de arrays de strings formatadas
        
    Comentário: Retorna os jogos em formato JSON como array de arrays de strings.
    """
    jogos_json = []
    
    # Converte cada jogo para array de strings formatadas
    for jogo in jogos:
        jogo_formatado = [f"{n:02d}" for n in sorted(jogo)]
        jogos_json.append(jogo_formatado)
    
    # Retorna JSON formatado
    return json.dumps(jogos_json, indent=2, ensure_ascii=False)


def salvar_jogos_em_arquivo(conteudo_json: str, data_geracao: datetime, concurso_numero: int = None) -> str:
    """
    Salva o conteúdo em um arquivo JSON na pasta saida/jogos/ com prefixo agente_.
    
    Args:
        conteudo_json: Conteúdo do arquivo em formato JSON
        data_geracao: Data e hora da geração
        concurso_numero: Número do concurso usado (padrão: None, usa data/hora)
        
    Returns:
        Caminho do arquivo salvo
        
    Comentário: Cria o diretório se não existir e salva o arquivo com nome
    no formato: agente_CONCURSO.json ou agente_YYYYMMDD_HHMMSS_UUID.json (se concurso_numero for None)
    """
    diretorio_jogos = str(Path(__file__).resolve().parent.parent.parent / "saida" / "jogos")
    
    # Criar diretório se não existir
    if not os.path.exists(diretorio_jogos):
        os.makedirs(diretorio_jogos)
        print(f"📁 Diretório '{diretorio_jogos}' criado.")
    
    # Gera nome do arquivo: agente_CONCURSO.json ou agente_YYYYMMDD_HHMMSS_UUID.json
    if concurso_numero is not None:
        nome_arquivo = f"jogo_provavel_{concurso_numero}.json"
    else:
        data_arquivo = data_geracao.strftime("%Y%m%d_%H%M%S")
        identificador = str(uuid.uuid4())[:8]  # Primeiros 8 caracteres do UUID
        nome_arquivo = f"jogo_provavel_{data_arquivo}_{identificador}.json"
    caminho_arquivo = os.path.join(diretorio_jogos, nome_arquivo)
    
    # Salva o arquivo
    with open(caminho_arquivo, 'w', encoding='utf-8') as f:
        f.write(conteudo_json)
    
    return caminho_arquivo


# ============================================================================
# FUNÇÃO PRINCIPAL
# ============================================================================

def main():
    """
    Função principal do script.
    
    Coordena o carregamento de dados, cálculo de estatísticas, geração de jogos
    e apresentação dos resultados.
    """
    # Configurar parser de argumentos
    parser = argparse.ArgumentParser(
        description='Gerador de Jogos Sugeridos para Lotofácil - Análise Estatística',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:
  python gerador_jogos_lotofacil.py                    # Usa último concurso disponível, gera 10 jogos
  python gerador_jogos_lotofacil.py --concurso 3000     # Analisa até concurso 3000, gera 10 jogos
  python gerador_jogos_lotofacil.py --concurso 3000 -q 20  # Analisa até concurso 3000, gera 20 jogos
  python gerador_jogos_lotofacil.py --quantidade 15     # Gera 15 jogos usando último concurso disponível
        """
    )
    parser.add_argument(
        '--concurso', '-c',
        type=int,
        default=None,
        help='Número do concurso de referência. Os jogos serão gerados para o concurso SEGUINTE (N+1). (padrão: próximo concurso)'
    )
    parser.add_argument(
        '--quantidade', '-q',
        type=int,
        default=10,
        help='Quantidade de jogos a serem gerados. (padrão: 10)'
    )
    parser.add_argument(
        '--config-from-ml',
        type=str,
        default=None,
        help='Caminho para arquivo JSON de recomendação ML (ex: ml/recomendacao_concurso_3585.json)'
    )
    parser.add_argument(
        '--hibrido',
        action='store_true',
        help='Usar modo híbrido: ML (80%) + Estatística (20%)'
    )
    parser.add_argument(
        '--peso-ml',
        type=float,
        default=0.8,
        help='Peso do ML na mesclagem (0.0-1.0, padrão: 0.8)'
    )
    parser.add_argument(
        '--janela-ml',
        type=int,
        default=120,
        help='Janela de concursos para o modelo ML (padrão: 120)'
    )
    
    args = parser.parse_args()
    concurso_limite = args.concurso
    quantidade = args.quantidade
    ml_config_path = args.config_from_ml

    # Verificar ML antecipadamente
    ml_ok = _check_ml_disponivel()
    if ml_ok:
        print("✓ ML carregado com sucesso")

    # Carregar configuração ML se fornecida
    ml_params = None
    if ml_config_path:
        print("\n🤖 Modo ML Ativado")
        print("=" * 70)
        ml_params = carregar_config_ml(ml_config_path)
        if ml_params is None:
            print("⚠️  Continuando sem configuração ML...")
        print("=" * 70 + "\n")
    
    # Validar quantidade
    if quantidade < 1:
        print("❌ ERRO: A quantidade de jogos deve ser pelo menos 1.")
        return
    
    # print("="*70)
    # print(" GERADOR DE JOGOS SUGERIDOS - LOTOFÁCIL")
    # print(" Análise Estatística Baseada em Dados Históricos")
    # print("="*70)
    # print("\n⚠️  ATENÇÃO: Este é um script de análise estatística.")
    # print("   Os jogos gerados são apenas SUGESTÕES baseadas em padrões históricos.")
    # print("   NÃO há garantia de ganho. Use por sua conta e risco.\n")
    
    if concurso_limite:
        print(f"📋 Concurso de referência: {concurso_limite}")
    print(f"🎲 Quantidade de jogos a gerar: {quantidade}\n")
    
    # 1. Carregar dados históricos completos primeiro para validar concurso
    concursos_completos = carregar_dados_historicos(concurso_limite=None)
    
    if not concursos_completos:
        print("ERRO: Não foi possível carregar os dados históricos.")
        print("Verifique se o arquivo 'dados/numeros_sorteados.json' existe.")
        return
    
    # Validar se o concurso informado existe
    if concurso_limite is not None:
        numeros_concursos = {c['concurso'] for c in concursos_completos}
        if concurso_limite not in numeros_concursos:
            print(f"❌ ERRO: Concurso {concurso_limite} não encontrado nos dados!")
            if numeros_concursos:
                print(f"   Concursos disponíveis: {min(numeros_concursos)} até {max(numeros_concursos)}")
            return
    
    # Carregar dados filtrados
    concursos = carregar_dados_historicos(concurso_limite=concurso_limite)
    
    if not concursos:
        print("ERRO: Nenhum concurso encontrado após filtrar.")
        return
    
    # 2. Calcular estatísticas
    # print("\n📈 Calculando estatísticas históricas...")  # Retirado conforme solicitado
    estatisticas = {
        'frequencia': calcular_frequencia_numeros(concursos),
        'pares_impares': calcular_distribuicao_pares_impares(concursos),
        'somas': calcular_distribuicao_somas(concursos),
        'consecutivos': analisar_consecutivos(concursos)
    }
    # print("✓ Estatísticas calculadas com sucesso")  # Retirado conforme solicitado
    
    # 3. Imprimir estatísticas (removido)
    # imprimir_estatisticas(estatisticas, concursos)  # Estatísticas calculadas mas não exibidas
    
    # 4. Gerar jogos
    print(f"\n🎲 Gerando {quantidade} jogos sugeridos...")
    
    # Verificar modo híbrido
    usar_hibrido = args.hibrido
    peso_ml = args.peso_ml
    janela_ml = args.janela_ml
    
    if usar_hibrido:
        jogos = gerar_jogos_hibridos(concursos, estatisticas, 
                                      peso_ml=peso_ml, 
                                      janela_ml=janela_ml,
                                      quantidade=quantidade)
    else:
        jogos = gerar_jogos(concursos, estatisticas, quantidade=quantidade)
    # print(f"✓ {len(jogos)} jogos gerados com sucesso")
    
    # 5. Imprimir jogos
    ultimo_concurso = concursos[-1]['dezenas']
    imprimir_jogos(jogos, ultimo_concurso, estatisticas)
    
    # 6. Gerar conteúdo JSON e salvar em arquivo
    print("\n💾 Salvando jogos em arquivo...")
    data_geracao = datetime.now()
    conteudo_json = gerar_conteudo_markdown(jogos, ultimo_concurso, estatisticas, concursos)
    # O concurso para o qual estamos gerando é o PRÓXIMO após o concurso_limite
    # Ex: -c 3583 usa dados até 3582 e gera para o concurso 3584
    if concurso_limite is not None:
        numero_concurso_alvo = concurso_limite + 1
    else:
        numero_concurso_alvo = concursos[-1]['concurso'] + 1
    caminho_arquivo = salvar_jogos_em_arquivo(conteudo_json, data_geracao, concurso_numero=numero_concurso_alvo)
    print(f"✓ Jogos salvos em: {caminho_arquivo}")
    
    print("\n" + "="*70)
    print(" FIM DA ANÁLISE")
    # print("="*70)
    # # print("\nLembre-se: A Lotofácil é um jogo de azar. Mesmo com análise estatística,")
    # # print("não existem métodos garantidos de ganho. Aposte com responsabilidade!\n")


if __name__ == "__main__":
    main()
