FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml ./
COPY src/ src/
RUN pip install --no-cache-dir -e .

RUN mkdir -p dados saida

COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

ENV PYTHONPATH="/app/src:${PYTHONPATH}"

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/api/status')" || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "quina.interface.painel.server:app", \
     "--bind", "0.0.0.0:5000", \
     "--workers", "1", \
     "--threads", "4", \
     "--timeout", "600", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
