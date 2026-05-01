#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gerador de Jogos por Carteiras Estratégicas para Lotofácil
===========================================================

Este script gera jogos para 5 carteiras estratégicas distintas (A, B, C, D, E),
onde cada carteira segue uma estratégia específica e considera os jogos já
gerados pelas outras carteiras para diversificação e complementaridade.

Cada carteira salva seus jogos em arquivo separado:
saida/jogos/jogo_provavel_<letra>_<concurso>.json

IMPORTANTE: Este é um script de análise estatística. Os jogos gerados são
apenas sugestões baseadas em padrões históricos. NÃO há garantia de ganho.
"""

import json
import os
import random
import argparse
from typing import List, Dict, Tuple, Optional
from collections import Counter
from pathlib import Path
from datetime import datetime

# Adicionar diretório portfolio ao path
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'portfolio'))

# Importar funções do gerador principal
from gerador_jogos_lotofacil import (
    carregar_dados_historicos,
    calcular_frequencia_numeros,
    ajustar_soma_jogo,
    calcular_numeros_ausentes_ciclo,
    gerar_combinacao_estatistica,
    contar_pares_impares,
    calcular_soma,
    contar_repetidos_do_ultimo
)

# Importar funções do portfolio
from portfolio.utils import (
    calcular_percentil_soma,
    calcular_atraso_numeros
)

from portfolio.correlacao import (
    validar_diversidade,
    penalizar_correlacao_alta
)

from portfolio.carteiras import (
    ajustar_repeticao,
    gerar_jogo_base,
    gerar_recomendacao_ml
)


# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================

def calcular_pesos_ajustados(frequencia_numeros: Dict[int, int], 
                             jogos_existentes: List[List[int]]) -> Dict[int, float]:
    """
    Ajusta pesos de frequência considerando números já usados nos jogos existentes.
    Reduz peso de números muito frequentes nos jogos já gerados para balancear distribuição.
    
    Args:
        frequencia_numeros: Frequência histórica de cada número
        jogos_existentes: Lista de jogos já gerados pelas outras carteiras
        
    Returns:
        Dicionário com pesos ajustados para cada número
    """
    # Contar frequência de cada número nos jogos existentes
    frequencia_em_jogos = Counter()
    for jogo in jogos_existentes:
        for numero in jogo:
            frequencia_em_jogos[numero] += 1
    
    # Calcular pesos ajustados
    pesos_ajustados = {}
    total_jogos = len(jogos_existentes) if jogos_existentes else 1
    
    for numero in range(1, 26):
        # Peso base: frequência histórica
        peso_base = frequencia_numeros.get(numero, 0)
        
        # Penalização: se o número aparece muito nos jogos existentes
        frequencia_relativa = frequencia_em_jogos.get(numero, 0) / total_jogos
        
        # Reduzir peso se número está muito presente (penalização progressiva)
        if frequencia_relativa > 0.8:  # Aparece em mais de 80% dos jogos
            fator_penalizacao = 0.3
        elif frequencia_relativa > 0.6:  # Aparece em mais de 60% dos jogos
            fator_penalizacao = 0.5
        elif frequencia_relativa > 0.4:  # Aparece em mais de 40% dos jogos
            fator_penalizacao = 0.7
        else:
            fator_penalizacao = 1.0
        
        pesos_ajustados[numero] = peso_base * fator_penalizacao
    
    return pesos_ajustados


def salvar_carteira_json(jogos: List[List[int]], letra_carteira: str, 
                        concurso_numero: int) -> str:
    """
    Salva jogos de uma carteira em arquivo JSON.
    
    Args:
        jogos: Lista de jogos (cada jogo é lista de inteiros)
        letra_carteira: Letra da carteira (A, B, C, D ou E)
        concurso_numero: Número do concurso
        
    Returns:
        Caminho do arquivo salvo
    """
    diretorio_jogos = str(Path(__file__).resolve().parent.parent.parent / "saida" / "jogos")
    
    # Criar diretório se não existir
    if not os.path.exists(diretorio_jogos):
        os.makedirs(diretorio_jogos)
        print(f"📁 Diretório '{diretorio_jogos}' criado.")
    
    # Formatar jogos para strings
    jogos_formatados = [[f"{n:02d}" for n in sorted(jogo)] for jogo in jogos]
    
    # Gerar nome do arquivo
    nome_arquivo = f"jogo_provavel_{letra_carteira}_{concurso_numero}.json"
    caminho_arquivo = os.path.join(diretorio_jogos, nome_arquivo)
    
    # Salvar arquivo
    with open(caminho_arquivo, 'w', encoding='utf-8') as f:
        json.dump(jogos_formatados, f, indent=2, ensure_ascii=False)
    
    return caminho_arquivo


# ============================================================================
# GERAÇÃO DE CARTEIRAS
# ============================================================================

def gerar_carteira_a_conservadora(ultimo_concurso: List[int], 
                                  frequencia_numeros: Dict[int, int],
                                  concursos: List[Dict], quantidade: int,
                                  jogos_existentes: List[List[int]] = None) -> List[List[int]]:
    """
    Gera Carteira A - Conservadora.
    
    Estratégia:
    - Repetição: 9-11 dezenas do último concurso
    - Soma: faixa central (percentis 40-60)
    - Objetivo: consistência (9-10 acertos frequentes)
    - Performance estável, normalmente limitada a 11 acertos
    
    Args:
        ultimo_concurso: Dezenas do último concurso
        frequencia_numeros: Frequência histórica de cada número
        concursos: Lista de concursos históricos
        quantidade: Quantidade de jogos a gerar
        jogos_existentes: Jogos já gerados (para diversificação)
        
    Returns:
        Lista de jogos da carteira conservadora
    """
    if jogos_existentes is None:
        jogos_existentes = []
    
    # Calcular percentis de soma (faixa central)
    soma_p40 = calcular_percentil_soma(concursos, 0.40)
    soma_p60 = calcular_percentil_soma(concursos, 0.60)
    
    # Calcular pesos ajustados baseados em jogos existentes
    pesos_ajustados = calcular_pesos_ajustados(frequencia_numeros, jogos_existentes)
    
    jogos = []
    max_tentativas = 100
    
    for idx in range(quantidade):
        tentativas = 0
        jogo_valido = False
        
        while not jogo_valido and tentativas < max_tentativas:
            # Gerar jogo base
            variacao = idx % 10
            jogo = gerar_jogo_base(ultimo_concurso, frequencia_numeros, concursos, variacao)
            
            # Ajustar repetição (9-11)
            repeticao_alvo = 9 + (idx % 3)  # 9, 10 ou 11
            jogo = ajustar_repeticao(jogo, ultimo_concurso, repeticao_alvo)
            
            # Ajustar soma para faixa central
            jogo = ajustar_soma_jogo(jogo, int(soma_p40), int(soma_p60))
            
            # Validar diversidade
            valido, msg = validar_diversidade(jogo, jogos_existentes + jogos)
            if valido:
                jogos.append(sorted(jogo))
                jogo_valido = True
            else:
                tentativas += 1
        
        if not jogo_valido:
            # Fallback: usar jogo mesmo sem validação perfeita
            jogo = gerar_jogo_base(ultimo_concurso, frequencia_numeros, concursos, idx)
            jogo = ajustar_repeticao(jogo, ultimo_concurso, 10)
            jogo = ajustar_soma_jogo(jogo, int(soma_p40), int(soma_p60))
            jogos.append(sorted(jogo))
    
    return jogos


def gerar_carteira_b_balanceada(ultimo_concurso: List[int], 
                                 frequencia_numeros: Dict[int, int],
                                 concursos: List[Dict], quantidade: int,
                                 jogos_existentes: List[List[int]] = None) -> List[List[int]]:
    """
    Gera Carteira B - Estatística Balanceada.
    
    Estratégia:
    - Repetição: 7-8 dezenas
    - Equilíbrio entre todos os critérios estatísticos
    - Objetivo: 10-11 acertos
    - Boa média de acertos, mas raramente ultrapassa 11
    
    Args:
        ultimo_concurso: Dezenas do último concurso
        frequencia_numeros: Frequência histórica de cada número
        concursos: Lista de concursos históricos
        quantidade: Quantidade de jogos a gerar
        jogos_existentes: Jogos já gerados (para diversificação)
        
    Returns:
        Lista de jogos da carteira balanceada
    """
    if jogos_existentes is None:
        jogos_existentes = []
    
    # Calcular pesos ajustados
    pesos_ajustados = calcular_pesos_ajustados(frequencia_numeros, jogos_existentes)
    
    jogos = []
    max_tentativas = 100
    
    for idx in range(quantidade):
        tentativas = 0
        jogo_valido = False
        
        while not jogo_valido and tentativas < max_tentativas:
            # Gerar jogo base
            variacao = (idx + 20) % 10  # Variação diferente da conservadora
            jogo = gerar_jogo_base(ultimo_concurso, frequencia_numeros, concursos, variacao)
            
            # Ajustar repetição (7-8)
            repeticao_alvo = 7 + (idx % 2)  # 7 ou 8
            jogo = ajustar_repeticao(jogo, ultimo_concurso, repeticao_alvo)
            
            # Ajustar soma para faixa padrão (171-220)
            jogo = ajustar_soma_jogo(jogo, 171, 220)
            
            # Validar diversidade
            valido, msg = validar_diversidade(jogo, jogos_existentes + jogos)
            if valido:
                jogos.append(sorted(jogo))
                jogo_valido = True
            else:
                tentativas += 1
        
        if not jogo_valido:
            # Fallback
            jogo = gerar_jogo_base(ultimo_concurso, frequencia_numeros, concursos, idx + 20)
            jogo = ajustar_repeticao(jogo, ultimo_concurso, 8)
            jogo = ajustar_soma_jogo(jogo, 171, 220)
            jogos.append(sorted(jogo))
    
    return jogos


def gerar_carteira_c_agressiva(ultimo_concurso: List[int], 
                               frequencia_numeros: Dict[int, int],
                               concursos: List[Dict], quantidade: int,
                               jogos_existentes: List[List[int]] = None) -> List[List[int]]:
    """
    Gera Carteira C - Agressiva.
    
    Estratégia:
    - Repetição: 5-6 dezenas (baixa)
    - Forte peso em dezenas atrasadas
    - Soma: percentis 20-30 ou 70-80 (fora da mediana)
    - Objetivo: buscar 12+ acertos
    - Alta variância, aceita queda na média
    
    Args:
        ultimo_concurso: Dezenas do último concurso
        frequencia_numeros: Frequência histórica de cada número
        concursos: Lista de concursos históricos
        quantidade: Quantidade de jogos a gerar
        jogos_existentes: Jogos já gerados (para diversificação)
        
    Returns:
        Lista de jogos da carteira agressiva
    """
    if jogos_existentes is None:
        jogos_existentes = []
    
    # Calcular atrasos
    atrasos = calcular_atraso_numeros(concursos, 10)
    
    # Calcular percentis de soma (fora da mediana)
    soma_p20 = calcular_percentil_soma(concursos, 0.20)
    soma_p30 = calcular_percentil_soma(concursos, 0.30)
    soma_p70 = calcular_percentil_soma(concursos, 0.70)
    soma_p80 = calcular_percentil_soma(concursos, 0.80)
    
    # Calcular pesos ajustados
    pesos_ajustados = calcular_pesos_ajustados(frequencia_numeros, jogos_existentes)
    
    jogos = []
    max_tentativas = 100
    
    for idx in range(quantidade):
        tentativas = 0
        jogo_valido = False
        
        while not jogo_valido and tentativas < max_tentativas:
            # Gerar jogo base
            variacao = (idx + 40) % 10  # Variação diferente
            jogo = gerar_jogo_base(ultimo_concurso, frequencia_numeros, concursos, variacao)
            
            # Ajustar repetição (5-6 - baixa)
            repeticao_alvo = 5 + (idx % 2)  # 5 ou 6
            jogo = ajustar_repeticao(jogo, ultimo_concurso, repeticao_alvo)
            
            # Ajustar soma para faixa fora da mediana
            if idx % 2 == 0:
                # Soma baixa (percentis 20-30)
                jogo = ajustar_soma_jogo(jogo, int(soma_p20), int(soma_p30))
            else:
                # Soma alta (percentis 70-80)
                jogo = ajustar_soma_jogo(jogo, int(soma_p70), int(soma_p80))
            
            # Priorizar números atrasados (adicionar alguns)
            numeros_atrasados = [n for n, atraso in atrasos.items() if atraso >= 4]
            if numeros_atrasados:
                # Substituir alguns números por atrasados
                numeros_no_jogo = set(jogo)
                numeros_nao_atrasados = numeros_no_jogo - set(numeros_atrasados)
                if len(numeros_nao_atrasados) >= 3 and len(numeros_atrasados) >= 3:
                    trocar = random.sample(list(numeros_nao_atrasados), min(3, len(numeros_nao_atrasados)))
                    adicionar = random.sample(numeros_atrasados, min(3, len(numeros_atrasados)))
                    novo_jogo = [n for n in jogo if n not in trocar] + adicionar
                    jogo = sorted(novo_jogo[:15])
            
            # Validar diversidade
            valido, msg = validar_diversidade(jogo, jogos_existentes + jogos)
            if valido:
                jogos.append(sorted(jogo))
                jogo_valido = True
            else:
                tentativas += 1
        
        if not jogo_valido:
            # Fallback
            jogo = gerar_jogo_base(ultimo_concurso, frequencia_numeros, concursos, idx + 40)
            jogo = ajustar_repeticao(jogo, ultimo_concurso, 6)
            jogo = ajustar_soma_jogo(jogo, int(soma_p20), int(soma_p30))
            jogos.append(sorted(jogo))
    
    return jogos


def gerar_carteira_d_antipadrao(ultimo_concurso: List[int], 
                                frequencia_numeros: Dict[int, int],
                                concursos: List[Dict], quantidade: int,
                                jogos_existentes: List[List[int]] = None) -> List[List[int]]:
    """
    Gera Carteira D - Anti-padrão (Diferencial).
    
    Estratégia:
    - Quebra regras clássicas do modelo
    - Soma propositalmente fora do intervalo típico (<150 ou >240)
    - Menor dependência de padrões históricos
    - Objetivo: capturar eventos raros
    - Melhor performance histórica: 100% dos jogos ≥ 11 acertos, incluindo 13 acertos
    
    Args:
        ultimo_concurso: Dezenas do último concurso
        frequencia_numeros: Frequência histórica de cada número
        concursos: Lista de concursos históricos
        quantidade: Quantidade de jogos a gerar
        jogos_existentes: Jogos já gerados (para diversificação)
        
    Returns:
        Lista de jogos da carteira anti-padrão
    """
    if jogos_existentes is None:
        jogos_existentes = []
    
    jogos = []
    max_tentativas = 150  # Mais tentativas para quebrar padrões
    
    for idx in range(quantidade):
        tentativas = 0
        jogo_valido = False
        
        while not jogo_valido and tentativas < max_tentativas:
            # Gerar jogo base
            variacao = (idx + 60) % 10
            jogo = gerar_jogo_base(ultimo_concurso, frequencia_numeros, concursos, variacao)
            
            # Quebrar padrões
            if idx % 3 == 0:
                # Soma muito baixa (<150)
                jogo = ajustar_soma_jogo(jogo, 100, 149)
            elif idx % 3 == 1:
                # Soma muito alta (>240)
                jogo = ajustar_soma_jogo(jogo, 241, 300)
            else:
                # Distribuição extrema pares/ímpares
                jogo_set = set(jogo)
                pares_disponiveis = [n for n in range(2, 26, 2) if n <= 25]
                impares_disponiveis = [n for n in range(1, 26, 2) if n <= 25]
                
                if idx % 2 == 0:
                    # Muitos pares (10 pares / 5 ímpares)
                    impares_no_jogo = [n for n in jogo if n % 2 == 1]
                    trocar = random.sample(impares_no_jogo, min(5, len(impares_no_jogo)))
                    pares_adicionar = [p for p in pares_disponiveis if p not in jogo_set]
                    adicionar = random.sample(pares_adicionar, min(5, len(pares_adicionar)))
                    jogo = [n for n in jogo if n not in trocar] + adicionar
                else:
                    # Muitos ímpares (5 pares / 10 ímpares)
                    pares_no_jogo = [n for n in jogo if n % 2 == 0]
                    trocar = random.sample(pares_no_jogo, min(5, len(pares_no_jogo)))
                    impares_adicionar = [i for i in impares_disponiveis if i not in jogo_set]
                    adicionar = random.sample(impares_adicionar, min(5, len(impares_adicionar)))
                    jogo = [n for n in jogo if n not in trocar] + adicionar
            
            # Garantir 15 números
            jogo = sorted(list(set(jogo))[:15])
            while len(jogo) < 15:
                disponiveis = set(range(1, 26)) - set(jogo)
                if disponiveis:
                    jogo.append(random.choice(list(disponiveis)))
                else:
                    break
            jogo = sorted(jogo[:15])
            
            # Validar diversidade (mais permissivo para anti-padrão)
            valido, msg = validar_diversidade(jogo, jogos_existentes + jogos, 
                                             interseccao_maxima=10, interseccao_media_maxima=8.0)
            if valido:
                jogos.append(sorted(jogo))
                jogo_valido = True
            else:
                tentativas += 1
        
        if not jogo_valido:
            # Fallback: gerar jogo aleatório único
            jogo = sorted(random.sample(range(1, 26), 15))
            jogos.append(jogo)
    
    return jogos


def gerar_carteira_e_ml(ultimo_concurso: List[int], 
                        frequencia_numeros: Dict[int, int],
                        concursos: List[Dict], quantidade: int,
                        concurso_referencia: int,
                        jogos_existentes: List[List[int]] = None,
                        modelo_ml: str = None) -> List[List[int]]:
    """
    Gera Carteira E - ML Otimizada.
    
    Estratégia:
    - Utiliza diretamente as recomendações do modelo de Machine Learning
    - Otimiza P(max_hits ≥ 12)
    - Objetivo: maximizar métricas previstas pelo modelo
    - Desempenho abaixo do esperado, necessita ajustes e validação
    
    Args:
        ultimo_concurso: Dezenas do último concurso
        frequencia_numeros: Frequência histórica de cada número
        concursos: Lista de concursos históricos
        quantidade: Quantidade de jogos a gerar
        concurso_referencia: Número do concurso de referência
        jogos_existentes: Jogos já gerados (para diversificação)
        modelo_ml: Caminho para modelo ML (opcional)
        
    Returns:
        Lista de jogos da carteira ML
    """
    if jogos_existentes is None:
        jogos_existentes = []
    
    # Tentar obter recomendação ML
    params_ml = gerar_recomendacao_ml(concurso_referencia, modelo_ml)
    
    # Se não conseguir, usar parâmetros padrão balanceados
    if params_ml is None:
        params_ml = {
            'soma_min': 182,
            'soma_max': 212,
            'pares_min': 6,
            'pares_max': 9,
            'repetidos_min': 7,
            'repetidos_max': 10
        }
    
    # Calcular pesos ajustados
    pesos_ajustados = calcular_pesos_ajustados(frequencia_numeros, jogos_existentes)
    
    jogos = []
    max_tentativas = 100
    
    for idx in range(quantidade):
        tentativas = 0
        jogo_valido = False
        
        while not jogo_valido and tentativas < max_tentativas:
            # Gerar jogo base
            variacao = (idx + 80) % 10
            jogo = gerar_jogo_base(ultimo_concurso, frequencia_numeros, concursos, variacao)
            
            # Ajustar usando parâmetros ML
            repeticao_min = params_ml.get('repetidos_min', 7)
            repeticao_max = params_ml.get('repetidos_max', 10)
            repeticao_alvo = repeticao_min + (idx % (repeticao_max - repeticao_min + 1))
            jogo = ajustar_repeticao(jogo, ultimo_concurso, repeticao_alvo)
            
            # Ajustar soma usando parâmetros ML
            soma_min = params_ml.get('soma_min', 182)
            soma_max = params_ml.get('soma_max', 212)
            jogo = ajustar_soma_jogo(jogo, soma_min, soma_max)
            
            # Validar diversidade (mais rigoroso para ML)
            valido, msg = validar_diversidade(jogo, jogos_existentes + jogos)
            if valido:
                # Penalizar correlação com outras carteiras
                penalizacao = penalizar_correlacao_alta(jogo, jogos_existentes)
                if penalizacao < 50.0:  # Aceitar se penalização não for muito alta
                    jogos.append(sorted(jogo))
                    jogo_valido = True
                else:
                    tentativas += 1
            else:
                tentativas += 1
        
        if not jogo_valido:
            # Fallback
            jogo = gerar_jogo_base(ultimo_concurso, frequencia_numeros, concursos, idx + 80)
            jogo = ajustar_repeticao(jogo, ultimo_concurso, 8)
            jogo = ajustar_soma_jogo(jogo, params_ml.get('soma_min', 182), params_ml.get('soma_max', 212))
            jogos.append(sorted(jogo))
    
    return jogos


# ============================================================================
# FUNÇÃO PRINCIPAL DE GERAÇÃO
# ============================================================================

def gerar_todas_carteiras(concursos: List[Dict], concurso_referencia: int,
                          quantidades: Dict[str, int],
                          modelo_ml: Optional[str] = None) -> Dict[str, List[List[int]]]:
    """
    Gera todas as carteiras sequencialmente, cada uma considerando as anteriores.
    
    Args:
        concursos: Lista de concursos históricos (até concurso_referencia)
        concurso_referencia: Número do concurso de referência
        quantidades: Dicionário com quantidade de jogos por carteira
                    Ex: {'A': 10, 'B': 10, 'C': 5, 'D': 5, 'E': 10}
        modelo_ml: Caminho para modelo ML (opcional)
        
    Returns:
        Dicionário com jogos de cada carteira e arquivos salvos
    """
    if not concursos:
        raise ValueError("Lista de concursos vazia")
    
    # Calcular estatísticas básicas
    frequencia_numeros = calcular_frequencia_numeros(concursos)
    ultimo_concurso = concursos[-1]['dezenas']
    concurso_alvo = concurso_referencia + 1
    
    resultado = {
        'carteiras': {},
        'arquivos_salvos': {},
        'concurso_alvo': concurso_alvo,
        'concurso_referencia': concurso_referencia
    }
    
    # Acumular jogos já gerados para feedback
    todos_jogos_gerados = []
    
    print(f"\n{'='*70}")
    print(f"GERAÇÃO DE CARTEIRAS ESTRATÉGICAS - CONCURSO {concurso_alvo}")
    print(f"{'='*70}")
    print(f"Concurso de referência: {concurso_referencia}")
    print(f"Concurso alvo: {concurso_alvo}")
    print(f"{'='*70}\n")
    
    # Gerar Carteira A - Conservadora
    if quantidades.get('A', 0) > 0:
        print(f"📁 Gerando Carteira A - Conservadora ({quantidades['A']} jogos)...")
        carteira_a = gerar_carteira_a_conservadora(
            ultimo_concurso, frequencia_numeros, concursos,
            quantidades['A'], todos_jogos_gerados
        )
        resultado['carteiras']['A'] = carteira_a
        todos_jogos_gerados.extend(carteira_a)
        arquivo_a = salvar_carteira_json(carteira_a, 'A', concurso_alvo)
        resultado['arquivos_salvos']['A'] = arquivo_a
        print(f"✓ {len(carteira_a)} jogos gerados e salvos em: {arquivo_a}\n")
    
    # Gerar Carteira B - Balanceada
    if quantidades.get('B', 0) > 0:
        print(f"📁 Gerando Carteira B - Estatística Balanceada ({quantidades['B']} jogos)...")
        carteira_b = gerar_carteira_b_balanceada(
            ultimo_concurso, frequencia_numeros, concursos,
            quantidades['B'], todos_jogos_gerados
        )
        resultado['carteiras']['B'] = carteira_b
        todos_jogos_gerados.extend(carteira_b)
        arquivo_b = salvar_carteira_json(carteira_b, 'B', concurso_alvo)
        resultado['arquivos_salvos']['B'] = arquivo_b
        print(f"✓ {len(carteira_b)} jogos gerados e salvos em: {arquivo_b}\n")
    
    # Gerar Carteira C - Agressiva
    if quantidades.get('C', 0) > 0:
        print(f"📁 Gerando Carteira C - Agressiva ({quantidades['C']} jogos)...")
        carteira_c = gerar_carteira_c_agressiva(
            ultimo_concurso, frequencia_numeros, concursos,
            quantidades['C'], todos_jogos_gerados
        )
        resultado['carteiras']['C'] = carteira_c
        todos_jogos_gerados.extend(carteira_c)
        arquivo_c = salvar_carteira_json(carteira_c, 'C', concurso_alvo)
        resultado['arquivos_salvos']['C'] = arquivo_c
        print(f"✓ {len(carteira_c)} jogos gerados e salvos em: {arquivo_c}\n")
    
    # Gerar Carteira D - Anti-padrão
    if quantidades.get('D', 0) > 0:
        print(f"📁 Gerando Carteira D - Anti-padrão ({quantidades['D']} jogos)...")
        carteira_d = gerar_carteira_d_antipadrao(
            ultimo_concurso, frequencia_numeros, concursos,
            quantidades['D'], todos_jogos_gerados
        )
        resultado['carteiras']['D'] = carteira_d
        todos_jogos_gerados.extend(carteira_d)
        arquivo_d = salvar_carteira_json(carteira_d, 'D', concurso_alvo)
        resultado['arquivos_salvos']['D'] = arquivo_d
        print(f"✓ {len(carteira_d)} jogos gerados e salvos em: {arquivo_d}\n")
    
    # Gerar Carteira E - ML Otimizada
    if quantidades.get('E', 0) > 0:
        print(f"📁 Gerando Carteira E - ML Otimizada ({quantidades['E']} jogos)...")
        carteira_e = gerar_carteira_e_ml(
            ultimo_concurso, frequencia_numeros, concursos,
            quantidades['E'], concurso_referencia,
            todos_jogos_gerados, modelo_ml
        )
        resultado['carteiras']['E'] = carteira_e
        todos_jogos_gerados.extend(carteira_e)
        arquivo_e = salvar_carteira_json(carteira_e, 'E', concurso_alvo)
        resultado['arquivos_salvos']['E'] = arquivo_e
        print(f"✓ {len(carteira_e)} jogos gerados e salvos em: {arquivo_e}\n")
    
    # Resumo final
    total_jogos = sum(len(jogos) for jogos in resultado['carteiras'].values())
    print(f"{'='*70}")
    print(f"RESUMO FINAL")
    print(f"{'='*70}")
    print(f"Total de jogos gerados: {total_jogos}")
    for letra, jogos in resultado['carteiras'].items():
        print(f"  Carteira {letra}: {len(jogos)} jogos")
    print(f"{'='*70}\n")
    
    return resultado


# ============================================================================
# FUNÇÃO MAIN
# ============================================================================

def main():
    """
    Função principal do script.
    """
    parser = argparse.ArgumentParser(
        description='Gerador de Jogos por Carteiras Estratégicas - Lotofácil',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:
  python gerador_carteiras_lotofacil.py --concurso 3585
  python gerador_carteiras_lotofacil.py --concurso 3585 --carteira-a 15 --carteira-b 10
  python gerador_carteiras_lotofacil.py --concurso 3585 --carteira-a 20 --carteira-b 15 --carteira-c 10 --carteira-d 5 --carteira-e 10
  python gerador_carteiras_lotofacil.py --concurso 3585 --carteira-e 20 --modelo-ml ml/modelo.pkl
        """
    )

    dafault = 1
    
    parser.add_argument(
        '--concurso', '-c',
        type=int,
        default=dafault,
        help='Número do concurso de referência. Os jogos serão gerados para o concurso SEGUINTE (N+1). (padrão: último concurso disponível)'
    )
    
    parser.add_argument(
        '--carteira-a',
        type=int,
        default=dafault,
        help='Quantidade de jogos para carteira A - Conservadora (padrão: 10)'
    )
    
    parser.add_argument(
        '--carteira-b',
        type=int,
        default=dafault,
        help='Quantidade de jogos para carteira B - Estatística Balanceada (padrão: 10)'
    )
    
    parser.add_argument(
        '--carteira-c',
        type=int,
        default=dafault,
        help='Quantidade de jogos para carteira C - Agressiva (padrão: 10)'
    )
    
    parser.add_argument(
        '--carteira-d',
        type=int,
        default=dafault,
        help='Quantidade de jogos para carteira D - Anti-padrão (padrão: 10)'
    )
    
    parser.add_argument(
        '--carteira-e',
        type=int,
        default=dafault,
        help='Quantidade de jogos para carteira E - ML Otimizada (padrão: 10)'
    )
    
    parser.add_argument(
        '--modelo-ml',
        type=str,
        default=None,
        help='Caminho para modelo ML (opcional, para carteira E)'
    )
    
    args = parser.parse_args()
    
    # Validar quantidades
    quantidades = {
        'A': args.carteira_a,
        'B': args.carteira_b,
        'C': args.carteira_c,
        'D': args.carteira_d,
        'E': args.carteira_e
    }
    
    # Verificar se pelo menos uma carteira tem jogos
    total_quantidade = sum(quantidades.values())
    if total_quantidade == 0:
        print("❌ ERRO: Pelo menos uma carteira deve ter quantidade > 0")
        return
    
    # Validar quantidades mínimas
    for letra, qtd in quantidades.items():
        if qtd < 0:
            print(f"❌ ERRO: Quantidade para carteira {letra} deve ser >= 0")
            return
    
    # Carregar dados históricos completos primeiro para validar concurso
    concursos_completos = carregar_dados_historicos(concurso_limite=None)
    
    if not concursos_completos:
        print("❌ ERRO: Não foi possível carregar os dados históricos.")
        print("Verifique se o arquivo 'dados/numeros_sorteados.json' existe.")
        return
    
    # Determinar concurso de referência
    if args.concurso is not None:
        concurso_limite = args.concurso
        # Validar se o concurso informado existe
        numeros_concursos = {c['concurso'] for c in concursos_completos}
        if concurso_limite not in numeros_concursos:
            print(f"❌ ERRO: Concurso {concurso_limite} não encontrado nos dados!")
            if numeros_concursos:
                print(f"   Concursos disponíveis: {min(numeros_concursos)} até {max(numeros_concursos)}")
            return
    else:
        # Usar último concurso disponível
        concurso_limite = max(c['concurso'] for c in concursos_completos)
        print(f"📋 Usando último concurso disponível: {concurso_limite}")
    
    # Carregar dados filtrados
    concursos = carregar_dados_historicos(concurso_limite=concurso_limite)
    
    if not concursos:
        print("❌ ERRO: Nenhum concurso encontrado após filtrar.")
        return
    
    # Gerar todas as carteiras
    try:
        resultado = gerar_todas_carteiras(
            concursos, concurso_limite, quantidades, args.modelo_ml
        )
        
        print("✅ Geração de carteiras concluída com sucesso!")
        print(f"\nArquivos gerados:")
        for letra, arquivo in resultado['arquivos_salvos'].items():
            print(f"  Carteira {letra}: {arquivo}")
        
    except Exception as e:
        print(f"❌ ERRO durante a geração: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
