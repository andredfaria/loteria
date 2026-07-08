from quina.dominio.regras import FAIXAS_ACERTOS as REGRAS_FAIXAS
from quina.dominio.regras import NUMEROS_POR_SORTEIO as REGRAS_NPS
from quina.dominio.regras import TOTAL_NUMEROS as REGRAS_TOTAL
from quina.infra.config import (
    API_QUINA,
    DADOS_DIR,
    DB_PATH,
    FAIXAS_ACERTOS,
    NUMEROS_POR_SORTEIO,
    SAIDA_DIR,
    TOTAL_NUMEROS,
)


def test_game_constants_match_domain_rules():
    assert TOTAL_NUMEROS == REGRAS_TOTAL == 80
    assert NUMEROS_POR_SORTEIO == REGRAS_NPS == 5
    assert FAIXAS_ACERTOS == REGRAS_FAIXAS == [2, 3, 4, 5]


def test_api_endpoint():
    assert API_QUINA == "https://loteriascaixa-api.herokuapp.com/api/quina"


def test_dirs_exist():
    assert DADOS_DIR.exists()
    assert SAIDA_DIR.exists()
    assert DB_PATH.name == "quina.db"
