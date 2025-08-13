# FastAPI on Cloud Run
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY . .

# Cloud Run sets PORT. Default to 8080 for local runs.
ENV PORT=8080

# Start the API server and listen on 0.0.0.0:$PORT
CMD ["bash", "-lc", "exec uvicorn app:app --host 0.0.0.0 --port ${PORT}"]
