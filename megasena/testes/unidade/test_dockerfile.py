"""O HEALTHCHECK do Dockerfile precisa usar a rota sem login.

Consultar /api/status deixava o container sempre `unhealthy` quando
DASHBOARD_PASSWORD estava definida (a rota responde 401 sem sessão).
"""
from pathlib import Path

DOCKERFILE = Path(__file__).resolve().parents[2] / "Dockerfile"


def _bloco_healthcheck() -> str:
    texto = DOCKERFILE.read_text(encoding="utf-8")
    inicio = texto.index("HEALTHCHECK")
    fim = texto.find("\n\n", inicio)
    return texto[inicio:] if fim == -1 else texto[inicio:fim]


def test_healthcheck_usa_healthz():
    bloco = _bloco_healthcheck()
    assert "/healthz" in bloco
    assert "/api/" not in bloco
