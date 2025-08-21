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

COPY pyproject.toml README.md ./
COPY src/ src/
RUN uv pip install -e .

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
RUN uv pip install -e .[consumer]
COPY . .

FROM base-runtime AS consumer-runtime
COPY --from=consumer-builder /app/venv /app/venv
COPY --from=consumer-builder /app/src /app/src
COPY --from=consumer-builder /app/migrations /app/migrations
COPY --from=consumer-builder /app/alembic.ini /app/alembic.ini
CMD ["faststream", "run", "src.consumer.main:app"]

# ---------- Migrator ----------
FROM base-builder AS migrator-builder
RUN uv pip install -e .[migrator]
COPY . .

FROM base-runtime AS migrator-runtime
COPY --from=migrator-builder /app/venv /app/venv
COPY --from=migrator-builder /app/src /app/src
COPY --from=migrator-builder /app/migrations /app/migrations
COPY --from=migrator-builder /app/alembic.ini /app/alembic.ini
CMD ["alembic", "upgrade", "head"]

# ---------- Producer base ----------
FROM base-builder AS producer-builder
RUN uv pip install -e .[producer]
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

# ---------- Scheduler ----------
FROM base-builder AS scheduler-builder
RUN uv pip install -e .[scheduler]
COPY . .

FROM base-runtime AS scheduler-runtime
COPY --from=scheduler-builder /app/venv /app/venv
COPY --from=scheduler-builder /app/src /app/src
