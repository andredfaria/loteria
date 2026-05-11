#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para buscar dados dos concursos da lotofácil da API
e salvar localmente para análise posterior.
Opcionalmente também salva no banco de dados MySQL.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional
import requests


# Configurações
API_BASE_URL = "https://loteriascaixa-api.herokuapp.com/api/lotofacil"
DIRETORIO_DADOS = str(Path(__file__).resolve().parent.parent.parent / "dados")
DELAY_REQUISICOES = 0.5  # segundos entre requisições


def detectar_concurso_inicial() -> int:
    """Retorna o próximo concurso a buscar (maior existente + 1)."""
    arquivos = Path(DIRETORIO_DADOS).glob("concurso_*.json")
    numeros = []
    for f in arquivos:
        try:
            n = int(f.stem.split("_")[1])
            numeros.append(n)
        except (IndexError, ValueError):
            pass
    return max(numeros) + 1 if numeros else 1


def detectar_concurso_final() -> int:
    """Busca o número do concurso mais recente disponível na API."""
    url = f"{API_BASE_URL}/latest"
    response = requests.get(url, headers={"accept": "*/*"}, timeout=10)
    response.raise_for_status()
    return int(response.json()["concurso"])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Busca concursos da Lotofácil")
    parser.add_argument("--ate", type=int, default=None,
                        help="Número do concurso final (padrão: mais recente na API)")
    parser.add_argument("--salvar-banco", action="store_true",
                        help="Também salvar no banco de dados MySQL")
    parser.add_argument("--host", type=str, default="localhost",
                        help="Host do banco de dados")
    parser.add_argument("--user", type=str, default="",
                        help="Usuário do banco de dados")
    parser.add_argument("--password", type=str, default="",
                        help="Senha do banco de dados")
    parser.add_argument("--port", type=int, default=3306,
                        help="Porta do banco de dados")
    parser.add_argument("--database", type=str, default="",
                        help="Nome do banco de dados")
    return parser.parse_args()


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
    numero_concurso = dados["concurso"]
    arquivo = os.path.join(DIRETORIO_DADOS, f"concurso_{numero_concurso}.json")
    
    with open(arquivo, 'w', encoding='utf-8') as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)


def salvar_arquivo_consolidado(todos_concursos: List[Dict]):
    """Salva todos os concursos em um único arquivo JSON."""
    arquivo = os.path.join(DIRETORIO_DADOS, "concursos_3500_3583.json")
    
    with open(arquivo, 'w', encoding='utf-8') as f:
        json.dump(todos_concursos, f, ensure_ascii=False, indent=2)
    
    print(f"\n📦 Arquivo consolidado salvo: {arquivo}")


def salvar_numeros_sorteados_simplificado(todos_concursos: List[Dict]):
    """Salva apenas os números sorteados em formato simplificado para análise rápida."""
    arquivo = os.path.join(DIRETORIO_DADOS, "numeros_sorteados.json")

    # Carregar dados existentes para não perder histórico
    existentes = {}
    if os.path.exists(arquivo):
        with open(arquivo, 'r', encoding='utf-8') as f:
            try:
                for c in json.load(f):
                    existentes[c["concurso"]] = c
            except (json.JSONDecodeError, KeyError):
                pass

    for concurso in todos_concursos:
        num = concurso["concurso"]
        existentes[num] = {
            "concurso": num,
            "data": concurso.get("data", ""),
            "dezenas": concurso.get("dezenas", []),
            "dezenasOrdemSorteio": concurso.get("dezenasOrdemSorteio", [])
        }

    dados_finais = sorted(existentes.values(), key=lambda c: c["concurso"])

    with open(arquivo, 'w', encoding='utf-8') as f:
        json.dump(dados_finais, f, ensure_ascii=False, indent=2)

    print(f"📊 Arquivo simplificado salvo: {arquivo} ({len(dados_finais)} concursos)")


def conectar_banco(host: str, user: str, password: str, port: int, database: str):
    """Conecta ao banco de dados MySQL."""
    try:
        import mysql.connector
        from mysql.connector import Error
        conn = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            port=port,
            database=database,
            charset="utf8mb4",
            collation="utf8mb4_unicode_ci"
        )
        print("✅ Conectado ao banco de dados")
        return conn
    except Error as e:
        print(f"❌ Erro ao conectar ao banco: {e}")
        return None


def criar_tabelas(cursor):
    """Cria as tabelas se não existirem."""
    tabelas = [
        """CREATE TABLE IF NOT EXISTS concursos (
            concurso INTEGER PRIMARY KEY,
            loteria VARCHAR(50),
            data DATE NOT NULL,
            local_sorteio VARCHAR(255),
            acumulou TINYINT(1) NOT NULL,
            proximo_concurso INTEGER,
            data_proximo_concurso DATE,
            valor_arrecadado DECIMAL(15, 2),
            valor_acumulado_concurso_0_5 DECIMAL(15, 2),
            valor_acumulado_concurso_especial DECIMAL(15, 2),
            valor_acumulado_proximo_concurso DECIMAL(15, 2),
            valor_estimado_proximo_concurso DECIMAL(15, 2),
            observacao TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        """CREATE TABLE IF NOT EXISTS dezenas (
            id INT AUTO_INCREMENT PRIMARY KEY,
            concurso INTEGER NOT NULL,
            numero INTEGER NOT NULL,
            ordem_sorteio INTEGER NOT NULL,
            FOREIGN KEY (concurso) REFERENCES concursos(concurso) ON DELETE CASCADE,
            UNIQUE KEY unique_concurso_numero (concurso, numero)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        """CREATE TABLE IF NOT EXISTS premiacoes (
            id INT AUTO_INCREMENT PRIMARY KEY,
            concurso INTEGER NOT NULL,
            descricao VARCHAR(100) NOT NULL,
            faixa INTEGER NOT NULL,
            ganhadores INTEGER NOT NULL,
            valor_premio DECIMAL(15, 2) NOT NULL,
            FOREIGN KEY (concurso) REFERENCES concursos(concurso) ON DELETE CASCADE,
            UNIQUE KEY unique_concurso_faixa (concurso, faixa)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"""
    ]
    
    for sql in tabelas:
        cursor.execute(sql)


def converter_data(data_str):
    """Converte data DD/MM/YYYY para YYYY-MM-DD"""
    if not data_str:
        return None
    try:
        from datetime import datetime
        data_obj = datetime.strptime(data_str, '%d/%m/%Y')
        return data_obj.strftime('%Y-%m-%d')
    except:
        return None


def salvar_no_banco(conn, dados_concurso: Dict) -> bool:
    """Salva um concurso no banco de dados."""
    from mysql.connector import Error
    
    cursor = conn.cursor()
    try:
        numero = dados_concurso['concurso']
        
        # Insert/update concurso
        sql_concurso = """
            INSERT INTO concursos (
                concurso, loteria, data, local_sorteio, acumulou, proximo_concurso,
                data_proximo_concurso, valor_arrecadado, valor_acumulado_concurso_0_5,
                valor_acumulado_concurso_especial, valor_acumulado_proximo_concurso,
                valor_estimado_proximo_concurso, observacao
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                loteria = VALUES(loteria), data = VALUES(data),
                local_sorteio = VALUES(local_sorteio), acumulou = VALUES(acumulou),
                proximo_concurso = VALUES(proximo_concurso),
                data_proximo_concurso = VALUES(data_proximo_concurso),
                valor_arrecadado = VALUES(valor_arrecadado),
                valor_acumulado_concurso_0_5 = VALUES(valor_acumulado_concurso_0_5),
                valor_acumulado_concurso_especial = VALUES(valor_acumulado_concurso_especial),
                valor_acumulado_proximo_concurso = VALUES(valor_acumulado_proximo_concurso),
                valor_estimado_proximo_concurso = VALUES(valor_estimado_proximo_concurso),
                observacao = VALUES(observacao)
        """
        
        cursor.execute(sql_concurso, (
            numero,
            dados_concurso.get('loteria'),
            converter_data(dados_concurso.get('data')),
            dados_concurso.get('local'),
            1 if dados_concurso.get('acumulou', False) else 0,
            dados_concurso.get('proximoConcurso'),
            converter_data(dados_concurso.get('dataProximoConcurso')),
            dados_concurso.get('valorArrecadado'),
            dados_concurso.get('valorAcumuladoConcurso_0_5'),
            dados_concurso.get('valorAcumuladoConcursoEspecial'),
            dados_concurso.get('valorAcumuladoProximoConcurso'),
            dados_concurso.get('valorEstimadoProximoConcurso'),
            dados_concurso.get('observacao', '')
        ))
        
        # Insert dezenas
        dezenas_ordem = dados_concurso.get('dezenasOrdemSorteio', [])
        for idx, dezena in enumerate(dezenas_ordem, 1):
            numero_dezena = int(dezena)
            cursor.execute("""
                INSERT INTO dezenas (concurso, numero, ordem_sorteio)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE ordem_sorteio = VALUES(ordem_sorteio)
            """, (numero, numero_dezena, idx))
        
        # Insert premiacoes
        premiacoes = dados_concurso.get('premiacoes', [])
        for premio in premiacoes:
            cursor.execute("""
                INSERT INTO premiacoes (concurso, descricao, faixa, ganhadores, valor_premio)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    descricao = VALUES(descricao),
                    ganhadores = VALUES(ganhadores),
                    valor_premio = VALUES(valor_premio)
            """, (
                numero,
                premio.get('descricao'),
                premio.get('faixa'),
                premio.get('ganhadores'),
                premio.get('valorPremio')
            ))
        
        conn.commit()
        return True
        
    except Error as e:
        print(f"  ❌ Erro ao salvar concurso {dados_concurso.get('concurso')}: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()


def main():
    """Função principal que executa o processo de busca."""
    args = parse_args()
    concurso_inicial = detectar_concurso_inicial()
    concurso_final = args.ate if args.ate else detectar_concurso_final()

    if concurso_inicial > concurso_final:
        print(f"✅ Dados já atualizados até concurso {concurso_final}.")
        return

    print("=" * 60)
    print("Buscador de Concursos da Lotofácil")
    print(f"Concursos: {concurso_inicial} até {concurso_final}")
    print("=" * 60)

    # Conectar ao banco se solicitado
    conn_banco = None
    if args.salvar_banco:
        print("\n🔌 Conectando ao banco de dados...")
        conn_banco = conectar_banco(
            args.host, args.user, args.password, 
            args.port, args.database
        )
        if conn_banco:
            cursor = conn_banco.cursor()
            criar_tabelas(cursor)
            conn_banco.commit()
            cursor.close()

    criar_diretorio_dados()

    todos_concursos = []
    sucessos = 0
    falhas = 0
    ja_existentes = 0
    banco_sucessos = 0
    banco_falhas = 0

    total = concurso_final - concurso_inicial + 1

    print(f"\n🔍 Buscando {total} concursos...\n")

    for numero_concurso in range(concurso_inicial, concurso_final + 1):
        print(f"[{numero_concurso - concurso_inicial + 1}/{total}] Buscando concurso {numero_concurso}...", end=" ")
        
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
                
                # Salvar no banco se solicitado
                if conn_banco:
                    if salvar_no_banco(conn_banco, dados):
                        banco_sucessos += 1
                    else:
                        banco_falhas += 1
                        
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
                
                # Salvar no banco se solicitado
                if conn_banco:
                    if salvar_no_banco(conn_banco, dados):
                        banco_sucessos += 1
                        print("  💾 Salvo no banco")
                    else:
                        banco_falhas += 1
            else:
                falhas += 1
                print("❌ Falhou")
        
        # Delay entre requisições para não sobrecarregar a API
        if numero_concurso < concurso_final:
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
    
    if conn_banco:
        print(f"  💾 Banco - Sucessos: {banco_sucessos}")
        print(f"  💾 Banco - Falhas: {banco_falhas}")
        conn_banco.close()
        print("  🔌 Conexão fechada")
    
    print("=" * 60)
    print("\n✅ Processo concluído!")


if __name__ == "__main__":
    main()
