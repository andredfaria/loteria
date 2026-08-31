FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src/ src/
RUN pip install --no-cache-dir -e ".[dev]"

RUN mkdir -p dados saida 2>/dev/null || true

COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Roda a app como usuário sem privilégios — nenhum processo do dashboard
# (Flask/gunicorn, subprocess de treino/backtest) precisa de root. UID/GID
# fixos em 1000 para bind mounts de host previsíveis; volumes nomeados do
# Docker herdam o dono do diretório da imagem na primeira criação, então o
# chown abaixo já cobre dados/, saida/ e src/ (inclusive
# src/lotofacil/experimentos/saved_models, criado em runtime pelo treino).
RUN groupadd -r -g 1000 appuser && useradd -r -u 1000 -g appuser appuser \
    && chown -R appuser:appuser /app

ENV PYTHONPATH="/app/src:${PYTHONPATH}"
ENV DASHBOARD_HOST="0.0.0.0"
ENV DASHBOARD_PORT="5000"

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/api/status')" || exit 1

EXPOSE 5000

USER appuser

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "lotofacil.interface.painel.server:app", \
     "--bind", "0.0.0.0:5000", \
     "--workers", "1", \
     "--threads", "4", \
     "--timeout", "600", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
