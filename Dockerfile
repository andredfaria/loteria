FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libgomp1 git \
    && rm -rf /var/lib/apt/lists/*

COPY lotofacil/requirements.txt .
RUN pip install --no-cache-dir $(grep -v '^tensorflow' requirements.txt | grep -v '^#' | grep -v '^$' | tr '\n' ' ')

COPY lotofacil/ .

RUN pip install --no-cache-dir -e . --no-deps
RUN mkdir -p dados saida/jogos src/models_saved src/lotofacil_lab/saved_models

EXPOSE 5000

ENV DASHBOARD_HOST=0.0.0.0
ENV DASHBOARD_PORT=5000

ENV PYTHONPATH="/app/src:${PYTHONPATH}"
CMD ["python", "-m", "lotofacil.interface.painel.server"]
