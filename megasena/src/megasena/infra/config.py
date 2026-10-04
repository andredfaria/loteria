from pathlib import Path

from loteria_nucleo.dados.caminhos import caminhos_do_projeto
from megasena.dominio.regras import MEGASENA_SPEC

PROJETO_RAIZ = Path(__file__).resolve().parent.parent.parent.parent
_CAMINHOS = caminhos_do_projeto(MEGASENA_SPEC, PROJETO_RAIZ)
DADOS_DIR = _CAMINHOS.dados
SAIDA_DIR = _CAMINHOS.saida
MODELOS_DIR = SAIDA_DIR / "modelos"


def get_db_path() -> Path:
    return caminhos_do_projeto(MEGASENA_SPEC, PROJETO_RAIZ).banco


DB_PATH = get_db_path()

DADOS_DIR.mkdir(parents=True, exist_ok=True)
SAIDA_DIR.mkdir(parents=True, exist_ok=True)
MODELOS_DIR.mkdir(parents=True, exist_ok=True)

TOTAL_NUMEROS = 60
NUMEROS_POR_SORTEIO = 6
VALID_NUMBERS = set(range(1, TOTAL_NUMEROS + 1))
FAIXAS_ACERTOS = [4, 5, 6]

API_BASE_URL = "https://loteriascaixa-api.herokuapp.com/api"
API_MEGASENA = f"{API_BASE_URL}/megasena"
API_TIMEOUT = 30
API_RETRIES = 5
API_RETRY_MIN = 1
API_RETRY_MAX = 10
USER_AGENT = "megasena/0.1"

RANDOM_SEED = 42
RF_N_ESTIMATORS = 200
RF_MAX_DEPTH = 10
RF_MIN_SAMPLES_LEAF = 5
