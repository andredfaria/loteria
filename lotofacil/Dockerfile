FROM python:3.11-slim

WORKDIR /app

# System deps for LightGBM, XGBoost, Pillow etc.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libgomp1 git \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Install the package so `lotofacil` CLI is available in PATH
RUN pip install --no-cache-dir -e . --no-deps

# Persistent data dirs — mounted as volumes in production.
# Remove symlink if present (local dev artifact), then create real dirs.
RUN rm -f dados && mkdir -p dados saida/jogos src/models_saved src/lotofacil_lab/saved_models

EXPOSE 5000

ENV DASHBOARD_HOST=0.0.0.0
ENV DASHBOARD_PORT=5000

CMD ["python", "-m", "src.dashboard.server"]
