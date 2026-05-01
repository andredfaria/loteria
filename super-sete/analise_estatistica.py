#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agente de Análise Estatística para Super 7
Analisa dados históricos e gera recomendação estatística baseada em métricas matemáticas.
"""

import json
import os
import argparse
import math
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
from datetime import datetime


# Constantes
NUM_COLUNAS = 7
DIGITOS = list(range(10))  # 0-9
FREQ_ESPERADA_UNIFORME = 0.1  # 1/10
ENTROPIA_MAXIMA = math.log2(10)  # ≈ 3.32

# Pesos padrão para o score composto
PESOS_PADRAO = {
    'frequencia': 0.25,
    'atraso': 0.30,
    'tendencia': 0.20,
    'entropia': 0.10,
    'exploracao': 0.15
}

# Janela padrão para análise de tendência temporal
JANELA_TENDENCIA_PADRAO = 50


def carregar_dados_historicos(caminho_json: str) -> List[Dict]:
    """
    Carrega e valida dados históricos dos concursos da Super 7.
    
    Args:
        caminho_json: Caminho para o arquivo JSON com os dados
        
    Returns:
        Lista ordenada de dicionários com dados dos concursos
        
    Raises:
        FileNotFoundError: Se o arquivo não existir
        ValueError: Se os dados estiverem em formato inválido
    """
    if not os.path.exists(caminho_json):
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho_json}")
    
    with open(caminho_json, 'r', encoding='utf-8') as f:
        dados = json.load(f)
    
    if not isinstance(dados, list):
        raise ValueError("O arquivo JSON deve conter uma lista de concursos")
    
    # Validar e ordenar por número de concurso
    concursos_validos = []
    for item in dados:
        if not isinstance(item, dict):
            continue
        
        concurso = item.get('concurso')
        dezenas = item.get('dezenas', [])
        
        # Validar estrutura
        if concurso is None or not dezenas:
            continue
        
        # Validar que há exatamente 7 dígitos
        if len(dezenas) != NUM_COLUNAS:
            continue
        
        # Validar que todos são dígitos válidos (0-9)
        try:
            digitos_validos = all(
                d.isdigit() and 0 <= int(d) <= 9 
                for d in dezenas
            )
            if not digitos_validos:
                continue
        except (ValueError, AttributeError):
            continue
        
        concursos_validos.append(item)
    
    # Ordenar por número de concurso
    concursos_validos.sort(key=lambda x: x.get('concurso', 0))
    
    if not concursos_validos:
        raise ValueError("Nenhum concurso válido encontrado no arquivo")
    
    return concursos_validos


def calcular_frequencias(dados_historicos: List[Dict]) -> Dict:
    """
    Calcula frequências absolutas e relativas por dígito e coluna.
    
    Args:
        dados_historicos: Lista de concursos históricos
        
    Returns:
        Dicionário com frequências absolutas e relativas
    """
    total_concursos = len(dados_historicos)
    
    # Inicializar contadores: freq_abs[coluna][digito] = contagem
    freq_abs = defaultdict(lambda: defaultdict(int))
    
    # Contar ocorrências
    for concurso in dados_historicos:
        dezenas = concurso.get('dezenas', [])
        for col_idx, digito_str in enumerate(dezenas, start=1):
            try:
                digito = int(digito_str)
                if 0 <= digito <= 9:
                    freq_abs[col_idx][digito] += 1
            except (ValueError, TypeError):
                continue
    
    # Calcular frequências relativas
    freq_rel = defaultdict(lambda: defaultdict(float))
    for coluna in range(1, NUM_COLUNAS + 1):
        for digito in DIGITOS:
            freq_rel[coluna][digito] = freq_abs[coluna][digito] / total_concursos
    
    return {
        'absolutas': dict(freq_abs),
        'relativas': dict(freq_rel),
        'total_concursos': total_concursos
    }


def calcular_atrasos(dados_historicos: List[Dict]) -> Dict:
    """
    Calcula o atraso (intervalo desde última ocorrência) para cada dígito em cada coluna.
    
    Args:
        dados_historicos: Lista de concursos históricos ordenados
        
    Returns:
        Dicionário com atrasos: atrasos[coluna][digito] = concursos desde última aparição
    """
    atrasos = defaultdict(lambda: defaultdict(int))
    
    # Rastrear última ocorrência de cada dígito em cada coluna
    ultima_ocorrencia = defaultdict(lambda: defaultdict(lambda: -1))
    
    # Processar concursos em ordem cronológica
    for idx, concurso in enumerate(dados_historicos):
        dezenas = concurso.get('dezenas', [])
        for col_idx, digito_str in enumerate(dezenas, start=1):
            try:
                digito = int(digito_str)
                if 0 <= digito <= 9:
                    ultima_ocorrencia[col_idx][digito] = idx
            except (ValueError, TypeError):
                continue
    
    # Calcular atrasos (último índice - última ocorrência)
    total_concursos = len(dados_historicos)
    for coluna in range(1, NUM_COLUNAS + 1):
        for digito in DIGITOS:
            ult_ocorr = ultima_ocorrencia[coluna][digito]
            if ult_ocorr >= 0:
                atrasos[coluna][digito] = total_concursos - 1 - ult_ocorr
            else:
                # Se nunca apareceu, considerar atraso máximo
                atrasos[coluna][digito] = total_concursos
    
    return dict(atrasos)


def calcular_desvio_uniforme(frequencias_relativas: Dict) -> Dict:
    """
    Calcula o desvio da distribuição uniforme esperada.
    
    Args:
        frequencias_relativas: Dicionário com frequências relativas por coluna/dígito
        
    Returns:
        Dicionário com desvios absolutos e quadráticos
    """
    desvios_abs = defaultdict(lambda: defaultdict(float))
    desvios_quad = defaultdict(lambda: defaultdict(float))
    
    for coluna in range(1, NUM_COLUNAS + 1):
        for digito in DIGITOS:
            freq_rel = frequencias_relativas.get(coluna, {}).get(digito, 0.0)
            desvio = abs(freq_rel - FREQ_ESPERADA_UNIFORME)
            desvios_abs[coluna][digito] = desvio
            desvios_quad[coluna][digito] = (freq_rel - FREQ_ESPERADA_UNIFORME) ** 2
    
    return {
        'absoluto': dict(desvios_abs),
        'quadratico': dict(desvios_quad)
    }


def calcular_entropia(frequencias_relativas: Dict) -> Dict:
    """
    Calcula a entropia de Shannon por coluna.
    
    Args:
        frequencias_relativas: Dicionário com frequências relativas por coluna/dígito
        
    Returns:
        Dicionário com entropia por coluna e por dígito/coluna
    """
    entropia_colunas = {}
    entropia_digito_coluna = defaultdict(lambda: defaultdict(float))
    
    for coluna in range(1, NUM_COLUNAS + 1):
        entropia_total = 0.0
        for digito in DIGITOS:
            freq_rel = frequencias_relativas.get(coluna, {}).get(digito, 0.0)
            if freq_rel > 0:
                contribuicao = -freq_rel * math.log2(freq_rel)
                entropia_total += contribuicao
                entropia_digito_coluna[coluna][digito] = contribuicao
        
        entropia_colunas[coluna] = entropia_total
    
    return {
        'por_coluna': entropia_colunas,
        'por_digito_coluna': dict(entropia_digito_coluna)
    }


def calcular_tendencia_temporal(dados_historicos: List[Dict], 
                                 janela: int = JANELA_TENDENCIA_PADRAO) -> Dict:
    """
    Calcula tendência temporal comparando frequência recente vs histórica.
    
    Args:
        dados_historicos: Lista de concursos históricos
        janela: Número de concursos recentes para análise
        
    Returns:
        Dicionário com frequências recentes e diferença em relação à histórica
    """
    total_concursos = len(dados_historicos)
    if total_concursos < janela:
        janela = total_concursos
    
    # Calcular frequência histórica total
    freq_historica = calcular_frequencias(dados_historicos)
    
    # Calcular frequência nos últimos N concursos
    concursos_recentes = dados_historicos[-janela:]
    freq_recente = calcular_frequencias(concursos_recentes)
    
    # Calcular diferença (tendência)
    tendencia = defaultdict(lambda: defaultdict(float))
    
    for coluna in range(1, NUM_COLUNAS + 1):
        for digito in DIGITOS:
            freq_hist = freq_historica['relativas'].get(coluna, {}).get(digito, 0.0)
            freq_rec = freq_recente['relativas'].get(coluna, {}).get(digito, 0.0)
            tendencia[coluna][digito] = freq_rec - freq_hist
    
    return {
        'frequencia_recente': freq_recente['relativas'],
        'frequencia_historica': freq_historica['relativas'],
        'diferenca': dict(tendencia),
        'janela': janela
    }


def calcular_correlacao_temporal(dados_historicos: List[Dict]) -> Dict:
    """
    Calcula autocorrelação temporal fraca (lag 1-3) por coluna.
    
    Args:
        dados_historicos: Lista de concursos históricos
        
    Returns:
        Dicionário com correlações por lag e coluna
    """
    # Extrair sequências por coluna
    sequencias = {col: [] for col in range(1, NUM_COLUNAS + 1)}
    
    for concurso in dados_historicos:
        dezenas = concurso.get('dezenas', [])
        for col_idx, digito_str in enumerate(dezenas, start=1):
            try:
                digito = int(digito_str)
                if 0 <= digito <= 9:
                    sequencias[col_idx].append(digito)
            except (ValueError, TypeError):
                continue
    
    # Calcular autocorrelação para lags 1, 2, 3
    correlacoes = defaultdict(lambda: defaultdict(float))
    
    for coluna in range(1, NUM_COLUNAS + 1):
        seq = sequencias[coluna]
        n = len(seq)
        
        if n < 4:
            continue
        
        # Média
        media = sum(seq) / n
        
        # Variância
        variancia = sum((x - media) ** 2 for x in seq) / n
        
        if variancia == 0:
            continue
        
        # Autocorrelação para cada lag
        for lag in [1, 2, 3]:
            if n <= lag:
                continue
            
            covariancia = sum(
                (seq[i] - media) * (seq[i + lag] - media)
                for i in range(n - lag)
            ) / (n - lag)
            
            correlacoes[coluna][lag] = covariancia / variancia if variancia > 0 else 0.0
    
    return dict(correlacoes)


def calcular_score_digito(digito: int, 
                          coluna: int, 
                          metricas: Dict, 
                          pesos: Dict = None) -> float:
    """
    Calcula score composto para um dígito em uma coluna específica.
    
    Args:
        digito: Dígito (0-9)
        coluna: Coluna (1-7)
        metricas: Dicionário com todas as métricas calculadas
        pesos: Pesos para cada componente do score
        
    Returns:
        Score final (0-1, normalizado)
    """
    if pesos is None:
        pesos = PESOS_PADRAO
    
    scores_componentes = {}
    
    # 1. Score de Frequência
    freq_rel = metricas['frequencias']['relativas'].get(coluna, {}).get(digito, 0.0)
    # Normalizar: usar frequência relativa diretamente (já está em 0-1)
    scores_componentes['frequencia'] = freq_rel
    
    # 2. Score de Atraso
    atraso = metricas['atrasos'].get(coluna, {}).get(digito, 0)
    max_atraso = metricas.get('max_atraso', 1)
    score_atraso = atraso / max_atraso if max_atraso > 0 else 0.0
    scores_componentes['atraso'] = min(score_atraso, 1.0)  # Normalizar para 0-1
    
    # 3. Score de Tendência
    tendencia = metricas['tendencia']['diferenca'].get(coluna, {}).get(digito, 0.0)
    # Normalizar tendência: -1 a 1 -> 0 a 1
    score_tendencia = (tendencia + 1.0) / 2.0
    scores_componentes['tendencia'] = max(0.0, min(1.0, score_tendencia))
    
    # 4. Score de Entropia (penalização para baixa entropia)
    entropia_col = metricas['entropia']['por_coluna'].get(coluna, 0.0)
    # Normalizar entropia: 0 a ENTROPIA_MAXIMA -> 0 a 1
    score_entropia = entropia_col / ENTROPIA_MAXIMA if ENTROPIA_MAXIMA > 0 else 0.0
    scores_componentes['entropia'] = score_entropia
    
    # 5. Score de Exploração (bonus para dígitos raros)
    freq_rel = metricas['frequencias']['relativas'].get(coluna, {}).get(digito, 0.0)
    # Se frequência < esperada (0.1), dar bonus; se > esperada, penalizar
    if freq_rel < FREQ_ESPERADA_UNIFORME:
        # Bonus proporcional ao quão raro é
        score_exploracao = 1.0 - (freq_rel / FREQ_ESPERADA_UNIFORME)
    else:
        # Penalização proporcional ao quão frequente é
        score_exploracao = max(0.0, 1.0 - ((freq_rel - FREQ_ESPERADA_UNIFORME) / (1.0 - FREQ_ESPERADA_UNIFORME)))
    scores_componentes['exploracao'] = score_exploracao
    
    # Calcular score final ponderado
    score_final = sum(
        scores_componentes[componente] * pesos.get(componente, 0.0)
        for componente in scores_componentes
    )
    
    return score_final


def calcular_scores_todos_digitos(metricas: Dict, pesos: Dict = None) -> Dict:
    """
    Calcula scores para todos os dígitos em todas as colunas.
    
    Args:
        metricas: Dicionário com todas as métricas calculadas
        pesos: Pesos para cada componente do score
        
    Returns:
        Dicionário: scores[coluna][digito] = score
    """
    if pesos is None:
        pesos = PESOS_PADRAO
    
    # Calcular max_atraso para normalização
    max_atraso = 0
    for coluna in range(1, NUM_COLUNAS + 1):
        for digito in DIGITOS:
            atraso = metricas['atrasos'].get(coluna, {}).get(digito, 0)
            max_atraso = max(max_atraso, atraso)
    
    metricas['max_atraso'] = max_atraso if max_atraso > 0 else 1
    
    scores = defaultdict(lambda: defaultdict(float))
    
    for coluna in range(1, NUM_COLUNAS + 1):
        for digito in DIGITOS:
            score = calcular_score_digito(digito, coluna, metricas, pesos)
            scores[coluna][digito] = score
    
    return dict(scores)


def gerar_recomendacao(scores_por_coluna: Dict) -> List[int]:
    """
    Gera recomendação selecionando o melhor dígito por coluna baseado nos scores.
    
    Args:
        scores_por_coluna: Dicionário com scores por coluna/dígito
        
    Returns:
        Lista de 7 dígitos recomendados
    """
    recomendacao = []
    
    for coluna in range(1, NUM_COLUNAS + 1):
        scores_col = scores_por_coluna.get(coluna, {})
        
        if not scores_col:
            # Se não há scores, escolher aleatoriamente ou usar 0
            recomendacao.append(0)
            continue
        
        # Selecionar dígito com maior score
        melhor_digito = max(scores_col.items(), key=lambda x: x[1])[0]
        recomendacao.append(melhor_digito)
    
    # Validação
    if len(recomendacao) != NUM_COLUNAS:
        raise ValueError(f"Recomendação deve ter {NUM_COLUNAS} dígitos")
    
    if not all(0 <= d <= 9 for d in recomendacao):
        raise ValueError("Todos os dígitos devem estar no range 0-9")
    
    return recomendacao


def gerar_relatorio(recomendacao: List[int], 
                   metricas: Dict, 
                   scores: Dict,
                   dados_historicos: List[Dict],
                   pesos: Dict = None) -> str:
    """
    Gera relatório textual com a recomendação e explicação.
    
    Args:
        recomendacao: Lista de 7 dígitos recomendados
        metricas: Dicionário com todas as métricas
        scores: Dicionário com scores por coluna/dígito
        dados_historicos: Lista de concursos históricos
        pesos: Pesos usados no cálculo
        
    Returns:
        String com relatório formatado
    """
    if pesos is None:
        pesos = PESOS_PADRAO
    
    total_concursos = len(dados_historicos)
    primeiro_concurso = dados_historicos[0] if dados_historicos else {}
    ultimo_concurso = dados_historicos[-1] if dados_historicos else {}
    
    data_inicio = primeiro_concurso.get('data', 'N/A')
    data_fim = ultimo_concurso.get('data', 'N/A')
    
    relatorio = []
    relatorio.append("=" * 70)
    relatorio.append("RECOMENDAÇÃO ESTATÍSTICA - SUPER 7")
    relatorio.append("=" * 70)
    relatorio.append("")
    
    # Jogo recomendado
    relatorio.append(f"Jogo Recomendado: {' - '.join(map(str, recomendacao))}")
    relatorio.append("")
    
    # Estatísticas gerais
    relatorio.append("Estatísticas Gerais:")
    relatorio.append(f"  • Total de concursos analisados: {total_concursos}")
    relatorio.append(f"  • Período: {data_inicio} a {data_fim}")
    relatorio.append("")
    
    # Scores por coluna
    relatorio.append("Scores por Coluna:")
    for idx, digito in enumerate(recomendacao, start=1):
        score = scores.get(idx, {}).get(digito, 0.0)
        relatorio.append(f"  Coluna {idx}: Dígito {digito} (Score: {score:.4f})")
    relatorio.append("")
    
    # Métricas utilizadas
    relatorio.append("Métricas Utilizadas:")
    relatorio.append("  • Frequência histórica (absoluta e relativa)")
    relatorio.append("  • Atraso estatístico (intervalo desde última ocorrência)")
    relatorio.append(f"  • Tendência temporal (últimos {metricas.get('tendencia', {}).get('janela', JANELA_TENDENCIA_PADRAO)} concursos)")
    relatorio.append("  • Entropia informacional (Shannon)")
    relatorio.append("  • Desvio da distribuição uniforme")
    relatorio.append("")
    
    # Pesos utilizados
    relatorio.append("Pesos do Score Composto:")
    for componente, peso in pesos.items():
        relatorio.append(f"  • {componente.capitalize()}: {peso:.2f} ({peso*100:.0f}%)")
    relatorio.append("")
    
    # Explicação detalhada
    relatorio.append("Explicação Detalhada:")
    relatorio.append("")
    
    for idx, digito in enumerate(recomendacao, start=1):
        coluna = idx
        score = scores.get(coluna, {}).get(digito, 0.0)
        
        # Obter métricas específicas
        freq_rel = metricas['frequencias']['relativas'].get(coluna, {}).get(digito, 0.0)
        atraso = metricas['atrasos'].get(coluna, {}).get(digito, 0)
        tendencia = metricas['tendencia']['diferenca'].get(coluna, {}).get(digito, 0.0)
        
        relatorio.append(f"Coluna {coluna} - Dígito {digito}:")
        relatorio.append(f"  • Frequência relativa: {freq_rel:.4f} ({freq_rel*100:.2f}%)")
        relatorio.append(f"  • Atraso: {atraso} concursos desde última aparição")
        relatorio.append(f"  • Tendência: {tendencia:+.4f} (positivo = mais frequente recentemente)")
        relatorio.append(f"  • Score final: {score:.4f}")
        relatorio.append("")
    
    # Aviso importante
    relatorio.append("=" * 70)
    relatorio.append("AVISO IMPORTANTE:")
    relatorio.append("Esta é uma recomendação estatística baseada exclusivamente em")
    relatorio.append("análise histórica e métricas matemáticas. O sorteio da Super 7")
    relatorio.append("é um processo aleatório e independente. Não há garantia de acerto,")
    relatorio.append("e esta recomendação não aumenta a probabilidade matemática real")
    relatorio.append("de ganhar. Use esta análise como ferramenta exploratória, não")
    relatorio.append("como previsão determinística.")
    relatorio.append("=" * 70)
    
    return "\n".join(relatorio)


def main():
    """Função principal que orquestra todo o processo de análise."""
    parser = argparse.ArgumentParser(
        description='Análise Estatística e Recomendação para Super 7',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--arquivo',
        type=str,
        default='dados/numeros_sorteados.json',
        help='Caminho para o arquivo JSON com dados históricos (padrão: dados_supersete/numeros_sorteados.json)'
    )
    
    parser.add_argument(
        '--janela',
        type=int,
        default=JANELA_TENDENCIA_PADRAO,
        help=f'Janela de concursos para análise de tendência temporal (padrão: {JANELA_TENDENCIA_PADRAO})'
    )
    
    parser.add_argument(
        '--peso-frequencia',
        type=float,
        default=PESOS_PADRAO['frequencia'],
        help=f"Peso para componente de frequência (padrão: {PESOS_PADRAO['frequencia']})"
    )
    
    parser.add_argument(
        '--peso-atraso',
        type=float,
        default=PESOS_PADRAO['atraso'],
        help=f"Peso para componente de atraso (padrão: {PESOS_PADRAO['atraso']})"
    )
    
    parser.add_argument(
        '--peso-tendencia',
        type=float,
        default=PESOS_PADRAO['tendencia'],
        help=f"Peso para componente de tendência (padrão: {PESOS_PADRAO['tendencia']})"
    )
    
    parser.add_argument(
        '--peso-entropia',
        type=float,
        default=PESOS_PADRAO['entropia'],
        help=f"Peso para componente de entropia (padrão: {PESOS_PADRAO['entropia']})"
    )
    
    parser.add_argument(
        '--peso-exploracao',
        type=float,
        default=PESOS_PADRAO['exploracao'],
        help=f"Peso para componente de exploração (padrão: {PESOS_PADRAO['exploracao']})"
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Modo verbose: exibe métricas detalhadas'
    )
    
    args = parser.parse_args()
    
    # Construir pesos personalizados
    pesos = {
        'frequencia': args.peso_frequencia,
        'atraso': args.peso_atraso,
        'tendencia': args.peso_tendencia,
        'entropia': args.peso_entropia,
        'exploracao': args.peso_exploracao
    }
    
    # Normalizar pesos (somar 1.0)
    soma_pesos = sum(pesos.values())
    if soma_pesos > 0:
        pesos = {k: v / soma_pesos for k, v in pesos.items()}
    
    try:
        # 1. Carregar dados históricos
        print("Carregando dados históricos...")
        dados_historicos = carregar_dados_historicos(args.arquivo)
        print(f"✓ {len(dados_historicos)} concursos carregados")
        
        # 2. Calcular todas as métricas
        print("\nCalculando métricas estatísticas...")
        
        print("  • Frequências...")
        frequencias = calcular_frequencias(dados_historicos)
        
        print("  • Atrasos...")
        atrasos = calcular_atrasos(dados_historicos)
        
        print("  • Desvios da distribuição uniforme...")
        desvios = calcular_desvio_uniforme(frequencias['relativas'])
        
        print("  • Entropia informacional...")
        entropia = calcular_entropia(frequencias['relativas'])
        
        print("  • Tendência temporal...")
        tendencia = calcular_tendencia_temporal(dados_historicos, args.janela)
        
        print("  • Correlação temporal...")
        correlacao = calcular_correlacao_temporal(dados_historicos)
        
        # Consolidar métricas
        metricas = {
            'frequencias': frequencias,
            'atrasos': atrasos,
            'desvios': desvios,
            'entropia': entropia,
            'tendencia': tendencia,
            'correlacao': correlacao
        }
        
        print("✓ Todas as métricas calculadas")
        
        # 3. Calcular scores
        print("\nCalculando scores compostos...")
        scores = calcular_scores_todos_digitos(metricas, pesos)
        print("✓ Scores calculados")
        
        # 4. Gerar recomendação
        print("\nGerando recomendação...")
        recomendacao = gerar_recomendacao(scores)
        print("✓ Recomendação gerada")
        
        # 5. Gerar e exibir relatório
        print("\n" + "=" * 70)
        relatorio = gerar_relatorio(recomendacao, metricas, scores, dados_historicos, pesos)
        print(relatorio)
        
        # Modo verbose: exibir métricas adicionais
        if args.verbose:
            print("\n" + "=" * 70)
            print("MÉTRICAS DETALHADAS (Modo Verbose)")
            print("=" * 70)
            
            print("\nFrequências Relativas por Coluna:")
            for coluna in range(1, NUM_COLUNAS + 1):
                print(f"\nColuna {coluna}:")
                for digito in DIGITOS:
                    freq = frequencias['relativas'].get(coluna, {}).get(digito, 0.0)
                    print(f"  Dígito {digito}: {freq:.4f} ({freq*100:.2f}%)")
            
            print("\n\nEntropia por Coluna:")
            for coluna in range(1, NUM_COLUNAS + 1):
                ent = entropia['por_coluna'].get(coluna, 0.0)
                print(f"  Coluna {coluna}: {ent:.4f} (máxima: {ENTROPIA_MAXIMA:.4f})")
        
    except FileNotFoundError as e:
        print(f"❌ Erro: {e}")
        return 1
    except ValueError as e:
        print(f"❌ Erro de validação: {e}")
        return 1
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
