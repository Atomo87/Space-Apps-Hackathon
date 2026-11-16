FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CACHE_DIR=/tmp/geosafra-cache

WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY docs/rag ./docs/rag
COPY knowledge ./knowledge

# Uma instancia/worker: snapshots e recibos compartilham o mesmo SQLite local.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000} --workers 1"]
