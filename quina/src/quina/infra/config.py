"""Paths, game rules, and API config for the Quina project."""
from pathlib import Path

PROJETO_RAIZ = Path(__file__).resolve().parent.parent.parent.parent
DADOS_DIR = PROJETO_RAIZ / "dados"
SAIDA_DIR = PROJETO_RAIZ / "saida"
DB_PATH = DADOS_DIR / "quina.db"

DADOS_DIR.mkdir(parents=True, exist_ok=True)
SAIDA_DIR.mkdir(parents=True, exist_ok=True)

TOTAL_NUMEROS = 80
NUMEROS_POR_SORTEIO = 5
VALID_NUMBERS = set(range(1, TOTAL_NUMEROS + 1))
FAIXAS_ACERTOS = [2, 3, 4, 5]

API_BASE_URL = "https://loteriascaixa-api.herokuapp.com/api"
API_QUINA = f"{API_BASE_URL}/quina"
API_TIMEOUT = 30
API_RETRIES = 5
API_RETRY_MIN = 1
API_RETRY_MAX = 10
USER_AGENT = "quina-prediction/0.1"
