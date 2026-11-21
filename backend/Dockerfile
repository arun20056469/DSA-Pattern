FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DSA_DB_PATH=/data/dsa.db

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p /data

EXPOSE 8000

# Render/Railway inject PORT; fall back to 8000 for local Docker runs.
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
