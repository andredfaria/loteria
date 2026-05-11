#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Atualiza incrementalmente os concursos da Lotofácil.

Estratégia:
  - Detecta o próximo concurso a buscar (maior arquivo existente + 1).
  - Faz GET sequencial em https://loteriascaixa-api.herokuapp.com/api/lotofacil/{N}.
  - Para automaticamente após 3 erros consecutivos.
  - Para cada resposta válida: salva JSON em dados/ e insere no banco SQLite.
"""

import json
import logging
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# Caminhos
# ---------------------------------------------------------------------------
_SCRIPT_DIR = Path(__file__).resolve().parent          # src/coleta/
_PROJECT_ROOT = _SCRIPT_DIR.parent.parent              # lotofacil/
DADOS_DIR = _PROJECT_ROOT / "dados"
DB_PATH = _PROJECT_ROOT / "app" / "lotofacil.db"

# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------
API_BASE = "https://loteriascaixa-api.herokuapp.com/api/lotofacil"
REQUEST_TIMEOUT = 15        # segundos
DELAY_ENTRE_REQUISICOES = 0.5  # segundos
MAX_ERROS_CONSECUTIVOS = 3

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Banco de dados (SQLite)
# ---------------------------------------------------------------------------

@contextmanager
def _conectar(db_path: Path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def inicializar_banco(db_path: Path) -> None:
    """Garante que as tabelas existam."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with _conectar(db_path) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS concursos (
                concurso  INTEGER PRIMARY KEY,
                data      TEXT NOT NULL,
                dezenas   TEXT NOT NULL,
                raw_json  TEXT
            );
        """)
    log.debug("Banco inicializado: %s", db_path)


def upsert_concurso(db_path: Path, raw: dict) -> None:
    """Insere ou atualiza um concurso no banco SQLite."""
    concurso = int(raw["concurso"])
    data = str(raw.get("data", ""))
    dezenas = sorted(int(d) for d in raw["dezenas"])
    dezenas_json = json.dumps(dezenas)
    raw_json = json.dumps(raw, ensure_ascii=False)

    with _conectar(db_path) as conn:
        conn.execute(
            """INSERT INTO concursos (concurso, data, dezenas, raw_json)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(concurso) DO UPDATE SET
                   data     = excluded.data,
                   dezenas  = excluded.dezenas,
                   raw_json = excluded.raw_json""",
            (concurso, data, dezenas_json, raw_json),
        )


# ---------------------------------------------------------------------------
# Detecção do ponto de partida
# ---------------------------------------------------------------------------

def detectar_proximo_concurso() -> int:
    """Retorna o próximo número a buscar (maior existente em dados/ + 1)."""
    numeros = []
    for f in DADOS_DIR.glob("concurso_*.json"):
        try:
            numeros.append(int(f.stem.split("_")[1]))
        except (IndexError, ValueError):
            pass
    return max(numeros) + 1 if numeros else 1


# ---------------------------------------------------------------------------
# Requisição à API
# ---------------------------------------------------------------------------

def buscar_concurso(session: requests.Session, numero: int) -> dict | None:
    """
    Faz GET para o concurso informado.
    Retorna o dict com os dados ou None em caso de erro.
    """
    url = f"{API_BASE}/{numero}"
    try:
        resp = session.get(url, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.HTTPError as exc:
        log.warning("HTTP %s para concurso %d", exc.response.status_code, numero)
    except requests.exceptions.ConnectionError:
        log.warning("Falha de conexão para concurso %d", numero)
    except requests.exceptions.Timeout:
        log.warning("Timeout para concurso %d", numero)
    except requests.exceptions.RequestException as exc:
        log.warning("Erro na requisição para concurso %d: %s", numero, exc)
    except json.JSONDecodeError:
        log.warning("JSON inválido para concurso %d", numero)
    return None


# ---------------------------------------------------------------------------
# Salvamento de arquivo
# ---------------------------------------------------------------------------

def salvar_json(dados: dict) -> Path:
    numero = dados["concurso"]
    caminho = DADOS_DIR / f"concurso_{numero}.json"
    DADOS_DIR.mkdir(parents=True, exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
    return caminho


# ---------------------------------------------------------------------------
# Loop principal
# ---------------------------------------------------------------------------

def executar() -> None:
    inicializar_banco(DB_PATH)

    proximo = detectar_proximo_concurso()
    log.info("Iniciando busca a partir do concurso %d", proximo)
    log.info("Dados  → %s", DADOS_DIR)
    log.info("Banco  → %s", DB_PATH)

    session = requests.Session()
    session.headers.update({"accept": "*/*"})

    erros_consecutivos = 0
    salvos = 0
    concurso = proximo

    while True:
        log.info("Buscando concurso %d ...", concurso)
        dados = buscar_concurso(session, concurso)

        if dados is None:
            erros_consecutivos += 1
            log.warning(
                "Erro %d/%d consecutivo(s).",
                erros_consecutivos,
                MAX_ERROS_CONSECUTIVOS,
            )
            if erros_consecutivos >= MAX_ERROS_CONSECUTIVOS:
                log.info(
                    "Limite de %d erros consecutivos atingido. Encerrando.",
                    MAX_ERROS_CONSECUTIVOS,
                )
                break
        else:
            erros_consecutivos = 0

            # Salva arquivo JSON
            caminho = salvar_json(dados)
            log.info("  Arquivo salvo: %s", caminho.name)

            # Persiste no banco
            try:
                upsert_concurso(DB_PATH, dados)
                log.info("  Banco atualizado: concurso %d", dados["concurso"])
            except Exception as exc:
                log.error("  Falha ao salvar no banco (concurso %d): %s", concurso, exc)

            salvos += 1

        concurso += 1
        time.sleep(DELAY_ENTRE_REQUISICOES)

    log.info("Concluído. Concursos salvos nesta execução: %d", salvos)


if __name__ == "__main__":
    executar()
