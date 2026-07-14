import os
from pathlib import Path

PROJETO_RAIZ = Path(__file__).resolve().parent.parent.parent.parent
DADOS_DIR = PROJETO_RAIZ / "dados"
SAIDA_DIR = PROJETO_RAIZ / "saida"


def get_db_path() -> Path:
    return Path(os.environ.get("SUPERSETE_DB_PATH", str(DADOS_DIR / "supersete.db")))


DB_PATH = get_db_path()

DADOS_DIR.mkdir(parents=True, exist_ok=True)
SAIDA_DIR.mkdir(parents=True, exist_ok=True)

NUM_COLUNAS = 7
DIGITOS = set(range(10))
TOTAL_COMBINACOES = 10 ** NUM_COLUNAS

API_BASE_URL = "https://loteriascaixa-api.herokuapp.com/api"
API_SUPERSETE = f"{API_BASE_URL}/supersete"
API_TIMEOUT = 30
API_RETRIES = 5
API_RETRY_MIN = 1
API_RETRY_MAX = 10
USER_AGENT = "supersete/0.1"
