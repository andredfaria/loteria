import os
from pathlib import Path

PROJETO_RAIZ = Path(__file__).resolve().parent.parent.parent.parent
DADOS_DIR = PROJETO_RAIZ / "dados"
SAIDA_DIR = PROJETO_RAIZ / "saida"


def get_db_path() -> Path:
    return Path(os.environ.get("DIADESORTE_DB_PATH", str(DADOS_DIR / "diadesorte.db")))


DB_PATH = get_db_path()

DADOS_DIR.mkdir(parents=True, exist_ok=True)
SAIDA_DIR.mkdir(parents=True, exist_ok=True)

TOTAL_NUMEROS = 31
NUMEROS_POR_SORTEIO = 7
VALID_NUMBERS = set(range(1, TOTAL_NUMEROS + 1))
FAIXAS_ACERTOS = [4, 5, 6, 7]

TODOS_MESES = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]

API_BASE_URL = "https://loteriascaixa-api.herokuapp.com/api"
API_DIADESORTE = f"{API_BASE_URL}/diadesorte"
API_TIMEOUT = 30
API_RETRIES = 5
API_RETRY_MIN = 1
API_RETRY_MAX = 10
USER_AGENT = "diadesorte/0.1"
