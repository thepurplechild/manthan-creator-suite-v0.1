# backend/Dockerfile
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8080 \
    PYTHONPATH=/app

WORKDIR /app

# Copy ONLY backend into /app so module path is stable: /app/app.py etc.
COPY backend/ /app/

# Install deps (make sure requirements.txt is in backend/)
RUN pip install --no-cache-dir -r requirements.txt

# Run uvicorn directly and bind to Cloud Run port
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080", "--proxy-headers"]


# App source
COPY . .

# Cloud Run injects PORT; default to 8080 for local runs
ENV PORT=8080
EXPOSE 8080

# Start through the small runner so import errors print full tracebacks
CMD ["python", "serve.py"]
