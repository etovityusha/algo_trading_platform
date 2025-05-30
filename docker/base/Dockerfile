FROM python:3.12-slim as builder

WORKDIR /app

RUN apt-get update && apt-get install -y build-essential

RUN python -m pip install uv

COPY requirements/core.txt requirements/core.txt

RUN python -m venv /app/venv
ENV PATH="/app/venv/bin:$PATH"