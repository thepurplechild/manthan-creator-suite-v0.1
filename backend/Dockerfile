# syntax=docker/dockerfile:1

FROM python:3.11-slim

# Safe Python defaults
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

WORKDIR /app

# Minimal OS deps (certs for HTTPS, curl for debugging)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl && \
    rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# App source
COPY . .

# Cloud Run injects PORT; default to 8080 for local runs
ENV PORT=8080
EXPOSE 8080

# Start through the small runner so import errors print full tracebacks
CMD ["python", "serve.py"]
