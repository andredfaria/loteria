#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validador de Apostas - Lotofácil
=================================

Este script valida apostas da Lotofácil (15-20 números) com base em padrões
históricos e regras de probabilidade, fornecendo feedback racional sobre a
qualidade estatística do jogo.

IMPORTANTE: 
- Este é um sistema de análise estatística, SEM GARANTIA DE GANHO.
- A Lotofácil é um jogo de azar e cada sorteio é um evento independente.
- Não há métodos garantidos de ganho em jogos de loteria.
- Use com responsabilidade e dentro do seu orçamento pessoal.
"""

import json
import os
import sys
import statistics
import math
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from itertools import combinations

# Tentar importar colorama, usar fallback se não disponível
try:
    from colorama import Fore, Style, init
    init(autoreset=True)
    COLORAMA_AVAILABLE = True
except ImportError:
    COLORAMA_AVAILABLE = False
    # Códigos ANSI básicos como fallback
    class Fore:
        GREEN = '\033[92m'
        YELLOW = '\033[93m'
        RED = '\033[91m'
        CYAN = '\033[96m'
    class Style:
        RESET_ALL = '\033[0m'


# Configurações
DIRETORIO_DADOS = str(Path(__file__).resolve().parent.parent.parent / "dados")

# Constantes
NUMEROS_MOLDURA = {1, 2, 3, 4, 5, 6, 10, 11, 15, 16, 20, 21, 22, 23, 24, 25}
NUMEROS_PRIMOS = {2, 3, 5, 7, 11, 13, 17, 19, 23}


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
        return []
    
    arquivos = sorted(diretorio.glob("concurso_*.json"))
    numeros_concursos = []
    
    for arquivo in arquivos:
        try:
            numero = int(arquivo.stem.split("_")[1])
            numeros_concursos.append(numero)
        except (ValueError, IndexError):
            continue
    
    return sorted(numeros_concursos)


def carregar_todos_concursos() -> List[Dict]:
    """
    Carrega todos os concursos disponíveis.
    
    Returns:
        Lista de dicionários com dados de todos os concursos
    """
    numeros_concursos = encontrar_arquivos_concursos()
    concursos = []
    
    for numero in numeros_concursos:
        concurso = carregar_concurso(numero)
        if concurso:
            concursos.append(concurso)
    
    # Ordenar por número de concurso
    concursos.sort(key=lambda x: x.get("concurso", 0))
    
    return concursos


def obter_ultimo_concurso(concursos: List[Dict]) -> Optional[Dict]:
    """
    Obtém o último concurso (maior número).
    
    Args:
        concursos: Lista de concursos
        
    Returns:
        Dicionário do último concurso ou None
    """
    if not concursos:
        return None
    
    return max(concursos, key=lambda x: x.get("concurso", 0))


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
    Conta números da moldura e do miolo.
    
    Args:
        jogo: Lista de números
        
    Returns:
        Tupla (moldura, miolo)
    """
    moldura = sum(1 for n in jogo if n in NUMEROS_MOLDURA)
    miolo = len(jogo) - moldura
    return (moldura, miolo)


def contar_primos(jogo: List[int]) -> int:
    """
    Conta quantos números primos existem no jogo.
    
    Args:
        jogo: Lista de números
        
    Returns:
        Quantidade de números primos
    """
    return sum(1 for n in jogo if n in NUMEROS_PRIMOS)


def contar_repetidos_do_ultimo(jogo: List[int], ultimo_concurso: List[int]) -> int:
    """
    Conta quantos números do jogo foram sorteados no último concurso.
    
    Args:
        jogo: Lista de números da aposta
        ultimo_concurso: Lista de números do último concurso
        
    Returns:
        Quantidade de números repetidos
    """
    return sum(1 for n in jogo if n in ultimo_concurso)


def encontrar_maior_sequencia(jogo: List[int]) -> Dict:
    """
    Encontra a maior sequência de números consecutivos.
    
    Args:
        jogo: Lista de números (será ordenada)
        
    Returns:
        Dicionário com informações sobre a maior sequência
    """
    jogo_ordenado = sorted(jogo)
    
    if not jogo_ordenado:
        return {"tamanho": 0, "numeros": []}
    
    maior_seq = 1
    seq_atual = 1
    inicio_maior = 0
    inicio_atual = 0
    
    for i in range(1, len(jogo_ordenado)):
        if jogo_ordenado[i] == jogo_ordenado[i-1] + 1:
            seq_atual += 1
        else:
            if seq_atual > maior_seq:
                maior_seq = seq_atual
                inicio_maior = inicio_atual
            seq_atual = 1
            inicio_atual = i
    
    # Verificar última sequência
    if seq_atual > maior_seq:
        maior_seq = seq_atual
        inicio_maior = inicio_atual
    
    numeros_sequencia = jogo_ordenado[inicio_maior:inicio_maior + maior_seq]
    
    return {
        "tamanho": maior_seq,
        "numeros": numeros_sequencia
    }


def calcular_medias_historicas(concursos: List[Dict]) -> Dict:
    """
    Calcula médias históricas de todas as métricas.
    
    Args:
        concursos: Lista de concursos históricos
        
    Returns:
        Dicionário com médias e desvios padrão
    """
    somas = []
    pares_list = []
    impares_list = []
    molduras = []
    primos_list = []
    
    for concurso in concursos:
        dezenas = extrair_dezenas(concurso)
        if len(dezenas) != 15:
            continue
        
        somas.append(calcular_soma(dezenas))
        pares, impares = contar_pares_impares(dezenas)
        pares_list.append(pares)
        impares_list.append(impares)
        moldura, _ = contar_moldura_miolo(dezenas)
        molduras.append(moldura)
        primos_list.append(contar_primos(dezenas))
    
    def calc_stats(values):
        if not values:
            return {"media": 0, "desvio": 0, "min": 0, "max": 0}
        return {
            "media": statistics.mean(values),
            "desvio": statistics.stdev(values) if len(values) > 1 else 0,
            "min": min(values),
            "max": max(values)
        }
    
    return {
        "soma": calc_stats(somas),
        "pares": calc_stats(pares_list),
        "impares": calc_stats(impares_list),
        "moldura": calc_stats(molduras),
        "primos": calc_stats(primos_list),
        "total_concursos": len(concursos)
    }


def validar_pares_impares(aposta: List[int], media_historica: Dict) -> Dict:
    """
    Valida distribuição de pares e ímpares.
    
    Args:
        aposta: Lista de números da aposta
        media_historica: Dicionário com médias históricas
        
    Returns:
        Dicionário com resultado da validação
    """
    pares, impares = contar_pares_impares(aposta)
    media_pares = media_historica["pares"]["media"]
    media_impares = media_historica["impares"]["media"]
    desvio_pares = media_historica["pares"]["desvio"]
    
    # Verificar padrão ideal (7-8 ou 8-7)
    dentro_padrao_ideal = (pares, impares) in [(7, 8), (8, 7)]
    
    # Verificar se está próximo da média histórica (±1 desvio padrão)
    dentro_media = abs(pares - media_pares) <= desvio_pares
    
    status = "ok" if (dentro_padrao_ideal or dentro_media) else "alerta"
    
    return {
        "status": status,
        "pares": pares,
        "impares": impares,
        "media_pares": media_pares,
        "dentro_padrao_ideal": dentro_padrao_ideal,
        "dentro_media": dentro_media
    }


def validar_soma(aposta: List[int], media_historica: Dict) -> Dict:
    """
    Valida soma das dezenas.
    
    Args:
        aposta: Lista de números da aposta
        media_historica: Dicionário com médias históricas
        
    Returns:
        Dicionário com resultado da validação
    """
    soma = calcular_soma(aposta)
    media = media_historica["soma"]["media"]
    desvio = media_historica["soma"]["desvio"]
    
    # Verificar se está dentro de ±1 desvio padrão da média
    dentro_media = abs(soma - media) <= desvio
    
    # Verificar faixa ideal (171-220)
    dentro_faixa_ideal = 171 <= soma <= 220
    
    status = "ok" if (dentro_faixa_ideal or dentro_media) else "alerta"
    
    return {
        "status": status,
        "soma": soma,
        "media": media,
        "desvio": desvio,
        "dentro_faixa_ideal": dentro_faixa_ideal,
        "dentro_media": dentro_media
    }


def validar_moldura(aposta: List[int], media_historica: Dict) -> Dict:
    """
    Valida quantidade de números da moldura.
    
    Args:
        aposta: Lista de números da aposta
        media_historica: Dicionário com médias históricas
        
    Returns:
        Dicionário com resultado da validação
    """
    moldura, miolo = contar_moldura_miolo(aposta)
    media = media_historica["moldura"]["media"]
    desvio = media_historica["moldura"]["desvio"]
    
    # Verificar padrão ideal (8-11)
    dentro_padrao_ideal = 8 <= moldura <= 11
    
    # Verificar se está próximo da média histórica
    dentro_media = abs(moldura - media) <= desvio
    
    status = "ok" if (dentro_padrao_ideal or dentro_media) else "alerta"
    
    return {
        "status": status,
        "moldura": moldura,
        "miolo": miolo,
        "media": media,
        "dentro_padrao_ideal": dentro_padrao_ideal,
        "dentro_media": dentro_media
    }


def validar_primos(aposta: List[int], media_historica: Dict) -> Dict:
    """
    Valida quantidade de números primos.
    
    Args:
        aposta: Lista de números da aposta
        media_historica: Dicionário com médias históricas
        
    Returns:
        Dicionário com resultado da validação
    """
    primos = contar_primos(aposta)
    media = media_historica["primos"]["media"]
    desvio = media_historica["primos"]["desvio"]
    
    # Verificar padrão ideal (4-7)
    dentro_padrao_ideal = 4 <= primos <= 7
    
    # Verificar se está próximo da média histórica
    dentro_media = abs(primos - media) <= desvio
    
    status = "ok" if (dentro_padrao_ideal or dentro_media) else "alerta"
    
    return {
        "status": status,
        "primos": primos,
        "media": media,
        "dentro_padrao_ideal": dentro_padrao_ideal,
        "dentro_media": dentro_media
    }


def comparar_ultimo_concurso(aposta: List[int], ultimo_concurso: List[int]) -> Dict:
    """
    Compara aposta com último concurso.
    
    Args:
        aposta: Lista de números da aposta
        ultimo_concurso: Lista de números do último concurso
        
    Returns:
        Dicionário com resultado da comparação
    """
    repetidos = contar_repetidos_do_ultimo(aposta, ultimo_concurso)
    dentro_padrao_ideal = 8 <= repetidos <= 10
    
    return {
        "status": "ok" if dentro_padrao_ideal else "alerta",
        "repetidos": repetidos,
        "dentro_padrao_ideal": dentro_padrao_ideal
    }


def gerar_subconjuntos_15(aposta: List[int]) -> List[List[int]]:
    """
    Gera todos os subconjuntos de 15 números de uma aposta maior.
    
    Args:
        aposta: Lista com 16-20 números
        
    Returns:
        Lista de listas, cada uma com 15 números
    """
    if len(aposta) < 15:
        return []
    
    if len(aposta) == 15:
        return [sorted(aposta)]
    
    # Gerar todas as combinações de 15 números
    subconjuntos = []
    for comb in combinations(aposta, 15):
        subconjuntos.append(sorted(list(comb)))
    
    return subconjuntos


def buscar_historico_acertos(aposta: List[int], concursos: List[Dict]) -> List[Dict]:
    """
    Busca no histórico concursos onde a aposta teria feito 14-15 pontos.
    
    Args:
        aposta: Lista de números da aposta (15-20 números)
        concursos: Lista de concursos históricos
        
    Returns:
        Lista de dicionários com informações dos concursos onde teria acertado 14-15
    """
    resultados = []
    
    # Se aposta tem 15 números, comparar diretamente
    if len(aposta) == 15:
        aposta_set = set(aposta)
        for concurso in concursos:
            dezenas = extrair_dezenas(concurso)
            if len(dezenas) != 15:
                continue
            
            dezenas_set = set(dezenas)
            acertos = len(aposta_set.intersection(dezenas_set))
            
            if acertos >= 14:
                numeros_acertados = sorted(list(aposta_set.intersection(dezenas_set)))
                resultados.append({
                    "concurso": concurso.get("concurso"),
                    "data": concurso.get("data", "N/A"),
                    "acertos": acertos,
                    "numeros_acertados": numeros_acertados
                })
    else:
        # Se aposta tem mais de 15 números, gerar subconjuntos
        subconjuntos = gerar_subconjuntos_15(aposta)
        
        for subconjunto in subconjuntos:
            subconjunto_set = set(subconjunto)
            for concurso in concursos:
                dezenas = extrair_dezenas(concurso)
                if len(dezenas) != 15:
                    continue
                
                dezenas_set = set(dezenas)
                acertos = len(subconjunto_set.intersection(dezenas_set))
                
                if acertos >= 14:
                    numeros_acertados = sorted(list(subconjunto_set.intersection(dezenas_set)))
                    # Verificar se já não existe este resultado
                    existe = False
                    for r in resultados:
                        if r["concurso"] == concurso.get("concurso") and r["acertos"] == acertos:
                            existe = True
                            break
                    
                    if not existe:
                        resultados.append({
                            "concurso": concurso.get("concurso"),
                            "data": concurso.get("data", "N/A"),
                            "acertos": acertos,
                            "numeros_acertados": numeros_acertados,
                            "subconjunto_usado": subconjunto
                        })
    
    # Ordenar por número de concurso
    resultados.sort(key=lambda x: x["concurso"])
    
    return resultados


def formatar_relatorio(aposta: List[int], validacoes: Dict, historico_acertos: List[Dict], 
                      sequencia_info: Dict, media_historica: Dict) -> None:
    """
    Formata e imprime o relatório completo.
    
    Args:
        aposta: Lista de números da aposta
        validacoes: Dicionário com resultados das validações
        historico_acertos: Lista de concursos onde teria acertado 14-15
        sequencia_info: Informações sobre sequências
        media_historica: Médias históricas
    """
    print("\n" + "=" * 80)
    print("RELATÓRIO DE VALIDAÇÃO - LOTOFÁCIL")
    print("=" * 80)
    print(f"\n📋 Aposta: {', '.join(f'{n:02d}' for n in sorted(aposta))}")
    print(f"📊 Total de números: {len(aposta)}")
    print()
    
    # Tabela de validações
    print("📈 VALIDAÇÕES ESTATÍSTICAS")
    print("-" * 80)
    print(f"{'Critério':<25} {'Status':<20} {'Valor Atual':<15} {'Ideal/Média':<20}")
    print("-" * 80)
    
    # Pares/Ímpares
    val_pi = validacoes["pares_impares"]
    status_str = f"{Fore.GREEN}✓ Dentro do Padrão{Style.RESET_ALL}" if val_pi["status"] == "ok" else f"{Fore.YELLOW}⚠ Fora do Padrão{Style.RESET_ALL}"
    valor_str = f"{val_pi['pares']}P/{val_pi['impares']}I"
    ideal_str = f"Média: {val_pi['media_pares']:.1f}P"
    print(f"{'Pares/Ímpares':<25} {status_str:<30} {valor_str:<15} {ideal_str:<20}")
    
    # Soma
    val_soma = validacoes["soma"]
    status_str = f"{Fore.GREEN}✓ Dentro do Padrão{Style.RESET_ALL}" if val_soma["status"] == "ok" else f"{Fore.YELLOW}⚠ Fora do Padrão{Style.RESET_ALL}"
    valor_str = str(val_soma["soma"])
    ideal_str = f"Média: {val_soma['media']:.1f} (±{val_soma['desvio']:.1f})"
    print(f"{'Soma':<25} {status_str:<30} {valor_str:<15} {ideal_str:<20}")
    
    # Moldura
    val_moldura = validacoes["moldura"]
    status_str = f"{Fore.GREEN}✓ Dentro do Padrão{Style.RESET_ALL}" if val_moldura["status"] == "ok" else f"{Fore.YELLOW}⚠ Fora do Padrão{Style.RESET_ALL}"
    valor_str = f"{val_moldura['moldura']}M/{val_moldura['miolo']}m"
    ideal_str = f"Média: {val_moldura['media']:.1f} (ideal: 8-11)"
    print(f"{'Moldura/Miolo':<25} {status_str:<30} {valor_str:<15} {ideal_str:<20}")
    
    # Primos
    val_primos = validacoes["primos"]
    status_str = f"{Fore.GREEN}✓ Dentro do Padrão{Style.RESET_ALL}" if val_primos["status"] == "ok" else f"{Fore.YELLOW}⚠ Fora do Padrão{Style.RESET_ALL}"
    valor_str = str(val_primos["primos"])
    ideal_str = f"Média: {val_primos['media']:.1f} (ideal: 4-7)"
    print(f"{'Números Primos':<25} {status_str:<30} {valor_str:<15} {ideal_str:<20}")
    
    # Repetidos do último
    val_repetidos = validacoes["repetidos"]
    status_str = f"{Fore.GREEN}✓ Dentro do Padrão{Style.RESET_ALL}" if val_repetidos["status"] == "ok" else f"{Fore.YELLOW}⚠ Fora do Padrão{Style.RESET_ALL}"
    valor_str = str(val_repetidos["repetidos"])
    ideal_str = "Ideal: 8-10"
    print(f"{'Repetidos do Último':<25} {status_str:<30} {valor_str:<15} {ideal_str:<20}")
    
    print()
    
    # Sequências
    print("🔢 SEQUÊNCIAS CONSECUTIVAS")
    print("-" * 80)
    if sequencia_info["tamanho"] > 1:
        print(f"Maior sequência: {sequencia_info['tamanho']} números")
        print(f"Números: {', '.join(f'{n:02d}' for n in sequencia_info['numeros'])}")
    else:
        print("Nenhuma sequência consecutiva encontrada")
    print()
    
    # Busca histórica
    print("🔍 BUSCA HISTÓRICA (14-15 pontos)")
    print("-" * 80)
    if historico_acertos:
        print(f"Encontrados {len(historico_acertos)} concurso(s) onde a aposta teria feito 14-15 pontos:\n")
        for resultado in historico_acertos:
            print(f"Concurso {resultado['concurso']:04d} ({resultado['data']}): {resultado['acertos']} acertos")
            if "subconjunto_usado" in resultado:
                print(f"  Subconjunto usado: {', '.join(f'{n:02d}' for n in resultado['subconjunto_usado'])}")
    else:
        print("Nenhum concurso encontrado onde a aposta teria feito 14-15 pontos.")
    print()
    
    # Resumo
    print("📊 RESUMO")
    print("-" * 80)
    alertas = sum(1 for v in validacoes.values() if v.get("status") == "alerta")
    total_validacoes = len(validacoes)
    aprovacoes = total_validacoes - alertas
    
    print(f"Validações aprovadas: {aprovacoes}/{total_validacoes}")
    print(f"Alertas: {alertas}/{total_validacoes}")
    
    if alertas == 0:
        print(f"\n{Fore.GREEN}✓ Aposta dentro de todos os padrões históricos!{Style.RESET_ALL}")
    elif alertas <= 2:
        print(f"\n{Fore.YELLOW}⚠ Aposta com alguns desvios dos padrões históricos.{Style.RESET_ALL}")
    else:
        print(f"\n{Fore.RED}⚠ Aposta com múltiplos desvios dos padrões históricos.{Style.RESET_ALL}")
    
    print()


def parse_aposta(entrada: str) -> List[int]:
    """
    Faz parse da entrada do usuário e valida.
    
    Args:
        entrada: String com números separados por vírgula
        
    Returns:
        Lista de inteiros validada
        
    Raises:
        ValueError: Se entrada for inválida
    """
    numeros = []
    for num_str in entrada.split(','):
        num_str = num_str.strip()
        try:
            numero = int(num_str)
            if 1 <= numero <= 25:
                numeros.append(numero)
            else:
                raise ValueError(f"Número {numero} fora do intervalo válido (1-25)")
        except ValueError as e:
            raise ValueError(f"Erro ao processar '{num_str}': {e}")
    
    # Validar quantidade
    if len(numeros) < 15 or len(numeros) > 20:
        raise ValueError(f"Aposta deve ter entre 15 e 20 números. Você forneceu {len(numeros)}.")
    
    # Validar duplicatas
    if len(set(numeros)) != len(numeros):
        raise ValueError("Números duplicados encontrados na aposta!")
    
    return sorted(numeros)


def main():
    """Função principal"""
    print("=" * 80)
    print("VALIDADOR DE APOSTAS - LOTOFÁCIL")
    print("=" * 80)
    print()
    
    # Verificar diretório
    if not os.path.exists(DIRETORIO_DADOS):
        print(f"❌ Erro: Diretório '{DIRETORIO_DADOS}' não encontrado!", file=sys.stderr)
        sys.exit(1)
    
    # Carregar dados históricos
    print("📂 Carregando dados históricos...")
    concursos = carregar_todos_concursos()
    
    if not concursos:
        print("❌ Erro: Nenhum concurso encontrado!", file=sys.stderr)
        sys.exit(1)
    
    print(f"✓ {len(concursos)} concursos carregados")
    
    # Calcular médias históricas
    print("📊 Calculando médias históricas...")
    media_historica = calcular_medias_historicas(concursos)
    print("✓ Médias calculadas")
    
    # Obter último concurso
    ultimo_concurso_dict = obter_ultimo_concurso(concursos)
    if ultimo_concurso_dict:
        ultimo_concurso = extrair_dezenas(ultimo_concurso_dict)
        print(f"✓ Último concurso: {ultimo_concurso_dict.get('concurso')} ({ultimo_concurso_dict.get('data', 'N/A')})")
    else:
        ultimo_concurso = []
        print("⚠ Último concurso não encontrado")
    
    print()
    
    # Entrada do usuário
    try:
        entrada = input("Digite sua aposta (15-20 números, separados por vírgula): ").strip()
        aposta = parse_aposta(entrada)
    except ValueError as e:
        print(f"❌ Erro: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nOperação cancelada pelo usuário.")
        sys.exit(0)
    
    print("\n🔍 Analisando aposta...")
    
    # Executar validações
    validacoes = {
        "pares_impares": validar_pares_impares(aposta, media_historica),
        "soma": validar_soma(aposta, media_historica),
        "moldura": validar_moldura(aposta, media_historica),
        "primos": validar_primos(aposta, media_historica),
        "repetidos": comparar_ultimo_concurso(aposta, ultimo_concurso) if ultimo_concurso else {"status": "ok", "repetidos": 0, "dentro_padrao_ideal": False}
    }
    
    # Encontrar sequências
    sequencia_info = encontrar_maior_sequencia(aposta)
    
    # Busca histórica (pode ser demorada se aposta tiver muitos números)
    if len(aposta) > 15:
        print(f"🔍 Buscando no histórico (isso pode demorar - testando {len(list(combinations(aposta, 15)))} combinações)...")
    else:
        print("🔍 Buscando no histórico...")
    
    historico_acertos = buscar_historico_acertos(aposta, concursos)
    
    # Gerar relatório
    formatar_relatorio(aposta, validacoes, historico_acertos, sequencia_info, media_historica)


if __name__ == "__main__":
    main()
