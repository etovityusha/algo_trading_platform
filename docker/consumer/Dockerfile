FROM trading-base AS builder

COPY requirements/consumer.txt requirements/consumer.txt
RUN uv pip install -r requirements/consumer.txt

COPY . .

FROM python:3.12-slim

WORKDIR /app

COPY --from=builder /app/venv /app/venv
COPY --from=builder /app/src /app/src
COPY --from=builder /app/migrations /app/migrations
COPY --from=builder /app/alembic.ini /app/alembic.ini

ENV PATH="/app/venv/bin:$PATH"
ENV PYTHONPATH=/app

CMD ["faststream", "run", "src.consumer.main:app"]
