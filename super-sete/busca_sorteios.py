#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para buscar dados dos concursos da Super Sete da API
e salvar localmente para análise posterior.
"""

import json
import os
import time
from typing import Dict, List, Optional
import requests


# Configurações
API_BASE_URL = "https://loteriascaixa-api.herokuapp.com/api/supersete"
CONCURSO_INICIAL = 830
CONCURSO_FINAL = 835
DIRETORIO_DADOS = "dados"
DELAY_REQUISICOES = 0.5  # segundos entre requisições


def criar_diretorio_dados():
    """Cria o diretório para armazenar os dados se não existir."""
    if not os.path.exists(DIRETORIO_DADOS):
        os.makedirs(DIRETORIO_DADOS)
        print(f"Diretório '{DIRETORIO_DADOS}' criado.")


def verificar_concurso_existe(numero_concurso: int) -> bool:
    """Verifica se o arquivo do concurso já existe."""
    arquivo = os.path.join(DIRETORIO_DADOS, f"concurso_{numero_concurso}.json")
    return os.path.exists(arquivo)


def buscar_concurso(numero_concurso: int) -> Optional[Dict]:
    """
    Faz requisição à API para buscar dados de um concurso específico.
    
    Args:
        numero_concurso: Número do concurso a ser buscado
        
    Returns:
        Dicionário com os dados do concurso ou None em caso de erro
    """
    url = f"{API_BASE_URL}/{numero_concurso}"
    headers = {"accept": "*/*"}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        print(f"  ⚠️  Erro HTTP {e.response.status_code} para concurso {numero_concurso}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"  ❌ Erro na requisição para concurso {numero_concurso}: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"  ❌ Erro ao decodificar JSON do concurso {numero_concurso}: {e}")
        return None


def salvar_concurso_individual(dados: Dict):
    """Salva os dados de um concurso em arquivo JSON individual."""
    numero_concurso = dados.get("concurso", "desconhecido")
    arquivo = os.path.join(DIRETORIO_DADOS, f"concurso_{numero_concurso}.json")
    
    with open(arquivo, 'w', encoding='utf-8') as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)


def salvar_arquivo_consolidado(todos_concursos: List[Dict]):
    """Salva todos os concursos em um único arquivo JSON."""
    if not todos_concursos:
        return
    
    primeiro_concurso = todos_concursos[0].get("concurso", CONCURSO_INICIAL)
    ultimo_concurso = todos_concursos[-1].get("concurso", CONCURSO_FINAL)
    arquivo = os.path.join(DIRETORIO_DADOS, f"concursos_{primeiro_concurso}_{ultimo_concurso}.json")
    
    with open(arquivo, 'w', encoding='utf-8') as f:
        json.dump(todos_concursos, f, ensure_ascii=False, indent=2)
    
    print(f"\n📦 Arquivo consolidado salvo: {arquivo}")


def salvar_numeros_sorteados_simplificado(todos_concursos: List[Dict]):
    """Salva apenas os números sorteados em formato simplificado para análise rápida."""
    dados_simplificados = []
    
    for concurso in todos_concursos:
        # Super Sete pode ter campos diferentes, vamos adaptar
        dados_base = {
            "concurso": concurso.get("concurso", ""),
            "data": concurso.get("data", ""),
        }
        
        # Adiciona números sorteados (pode variar o nome do campo na API)
        if "dezenas" in concurso:
            dados_base["dezenas"] = concurso["dezenas"]
        elif "listaDezenas" in concurso:
            dados_base["dezenas"] = concurso["listaDezenas"]
        elif "numeros" in concurso:
            dados_base["dezenas"] = concurso["numeros"]
        
        if "dezenasOrdemSorteio" in concurso:
            dados_base["dezenasOrdemSorteio"] = concurso["dezenasOrdemSorteio"]
        
        dados_simplificados.append(dados_base)
    
    arquivo = os.path.join(DIRETORIO_DADOS, "numeros_sorteados.json")
    
    with open(arquivo, 'w', encoding='utf-8') as f:
        json.dump(dados_simplificados, f, ensure_ascii=False, indent=2)
    
    print(f"📊 Arquivo simplificado salvo: {arquivo}")


def main():
    """Função principal que executa o processo de busca."""
    print("=" * 60)
    print("Buscador de Concursos da Super Sete")
    print(f"Concursos: {CONCURSO_INICIAL} até {CONCURSO_FINAL}")
    print("=" * 60)
    
    criar_diretorio_dados()
    
    todos_concursos = []
    sucessos = 0
    falhas = 0
    ja_existentes = 0
    
    total = CONCURSO_FINAL - CONCURSO_INICIAL + 1
    
    print(f"\n🔍 Buscando {total} concursos...\n")
    
    for numero_concurso in range(CONCURSO_INICIAL, CONCURSO_FINAL + 1):
        print(f"[{numero_concurso - CONCURSO_INICIAL + 1}/{total}] Buscando concurso {numero_concurso}...", end=" ")
        
        # Verifica se já existe
        if verificar_concurso_existe(numero_concurso):
            print("✅ Já existe, carregando...")
            arquivo = os.path.join(DIRETORIO_DADOS, f"concurso_{numero_concurso}.json")
            try:
                with open(arquivo, 'r', encoding='utf-8') as f:
                    dados = json.load(f)
                todos_concursos.append(dados)
                sucessos += 1
                ja_existentes += 1
            except Exception as e:
                print(f"❌ Erro ao carregar arquivo existente: {e}")
                falhas += 1
        else:
            # Busca na API
            dados = buscar_concurso(numero_concurso)
            
            if dados:
                salvar_concurso_individual(dados)
                todos_concursos.append(dados)
                sucessos += 1
                print("✅ Salvo")
            else:
                falhas += 1
                print("❌ Falhou")
        
        # Delay entre requisições para não sobrecarregar a API
        if numero_concurso < CONCURSO_FINAL:
            time.sleep(DELAY_REQUISICOES)
    
    # Salva arquivos consolidados
    if todos_concursos:
        print("\n💾 Salvando arquivos consolidados...")
        salvar_arquivo_consolidado(todos_concursos)
        salvar_numeros_sorteados_simplificado(todos_concursos)
    
    # Estatísticas finais
    print("\n" + "=" * 60)
    print("📈 Estatísticas:")
    print(f"  ✅ Sucessos: {sucessos}")
    print(f"  📁 Já existentes: {ja_existentes}")
    print(f"  ❌ Falhas: {falhas}")
    print(f"  📦 Total de concursos salvos: {len(todos_concursos)}")
    print("=" * 60)
    print("\n✅ Processo concluído!")


if __name__ == "__main__":
    main()
