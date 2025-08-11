# FastAPI on Cloud Run
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app
COPY pyproject.toml /app/

# Use pip to install due to slim image simplicity
RUN pip install --upgrade pip && pip install -r <(python - <<'PY'
import tomllib,sys
print('\n'.join(t for t in tomllib.load(open('pyproject.toml','rb'))['project']['dependencies']))
PY
) --no-cache-dir

COPY app.py /app/

# Cloud Run will set $PORT; default to 8080 for local
ENV PORT=8080
CMD exec uvicorn app:app --host 0.0.0.0 --port ${PORT}
