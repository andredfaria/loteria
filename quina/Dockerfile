FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml ./
COPY src/ src/
RUN pip install --no-cache-dir -e .

RUN mkdir -p dados saida

COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Roda a app como usuário sem privilégios — nada no dashboard precisa de
# root. UID/GID fixos em 1000 para bind mounts de host previsíveis; volumes
# nomeados do Docker herdam o dono do diretório da imagem na primeira
# criação, então o chown abaixo já cobre dados/ e saida/.
RUN groupadd -r -g 1000 appuser && useradd -r -u 1000 -g appuser appuser \
    && chown -R appuser:appuser /app

ENV PYTHONPATH="/app/src:${PYTHONPATH}"

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/api/status')" || exit 1

USER appuser

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "quina.interface.painel.server:app", \
     "--bind", "0.0.0.0:5000", \
     "--workers", "1", \
     "--threads", "4", \
     "--timeout", "600", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
