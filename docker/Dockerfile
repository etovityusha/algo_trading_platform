# syntax=docker/dockerfile:1.7

# ---------- Base builder ----------
FROM python:3.12-slim AS base-builder
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /app/venv
ENV PATH="/app/venv/bin:$PATH"

RUN pip install --no-cache-dir uv

# Core deps shared across all services
COPY requirements/core.txt requirements/core.txt
RUN uv pip install -r requirements/core.txt

# ---------- Base runtime ----------
FROM python:3.12-slim AS base-runtime
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=base-builder /app/venv /app/venv
ENV PATH="/app/venv/bin:$PATH"
ENV PYTHONPATH=/app

# ---------- Consumer ----------
FROM base-builder AS consumer-builder
COPY requirements/consumer.txt requirements/consumer.txt
RUN uv pip install -r requirements/consumer.txt
COPY . .

FROM base-runtime AS consumer-runtime
COPY --from=consumer-builder /app/venv /app/venv
COPY --from=consumer-builder /app/src /app/src
COPY --from=consumer-builder /app/migrations /app/migrations
COPY --from=consumer-builder /app/alembic.ini /app/alembic.ini
CMD ["faststream", "run", "src.consumer.main:app"]

# ---------- Migrator ----------
FROM base-builder AS migrator-builder
COPY requirements/migrator.txt requirements/migrator.txt
RUN uv pip install -r requirements/migrator.txt
COPY . .

FROM base-runtime AS migrator-runtime
COPY --from=migrator-builder /app/venv /app/venv
COPY --from=migrator-builder /app/src /app/src
COPY --from=migrator-builder /app/migrations /app/migrations
COPY --from=migrator-builder /app/alembic.ini /app/alembic.ini
CMD ["alembic", "upgrade", "head"]

# ---------- Producer base ----------
FROM base-builder AS producer-builder
COPY requirements/producer.txt requirements/producer.txt
RUN uv pip install -r requirements/producer.txt
COPY . .

FROM base-runtime AS producer-runtime
# Extra runtime libs for numpy/pandas/ta
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=producer-builder /app/venv /app/venv
COPY --from=producer-builder /app/src /app/src

# ---------- Trand producer ----------
FROM producer-runtime AS trand-runtime
CMD ["python", "-m", "src.producers.trand.main"]

