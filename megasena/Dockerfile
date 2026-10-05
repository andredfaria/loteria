FROM python:3.12-slim

WORKDIR /app

COPY nucleo/ /opt/nucleo/
RUN pip install --no-cache-dir -e "/opt/nucleo[painel,ml]"

COPY megasena/pyproject.toml megasena/README.md ./
COPY megasena/src/ src/
RUN pip install --no-cache-dir -e .

RUN mkdir -p dados saida

COPY megasena/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Roda a app como usuário sem privilégios — nada no dashboard precisa de
# root. UID/GID fixos em 1000 para bind mounts de host previsíveis; volumes
# nomeados do Docker herdam o dono do diretório da imagem na primeira
# criação, então o chown abaixo já cobre dados/ e saida/.
RUN groupadd -r -g 1000 appuser && useradd -r -u 1000 -g appuser appuser \
    && chown -R appuser:appuser /app

ENV PYTHONPATH="/app/src"

# Limita as threads de cálculo. Sem isso, n_jobs=-1 (sklearn/LightGBM), BLAS e
# TensorFlow enxergam todos os núcleos do host e um único treino ocupa o
# servidor inteiro. Para liberar mais núcleos, sobrescreva estas variáveis no
# EasyPanel (ver docs/deploy.md).
ENV OMP_NUM_THREADS="2" \
    OPENBLAS_NUM_THREADS="2" \
    MKL_NUM_THREADS="2" \
    LOKY_MAX_CPU_COUNT="2" \
    TF_NUM_INTRAOP_THREADS="2" \
    TF_NUM_INTEROP_THREADS="1"

EXPOSE 5000

HEALTHCHECK --interval=60s --timeout=5s --start-period=15s \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/healthz')" || exit 1

USER appuser

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "megasena.interface.painel.server:app", \
     "--bind", "0.0.0.0:5000", \
     "--workers", "1", \
     "--threads", "4", \
     "--timeout", "600", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
