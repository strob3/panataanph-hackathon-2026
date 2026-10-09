FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY src/backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY data/ ./data/

# Create persistent storage mountpoints
RUN mkdir -p /app/data /app/storage

ENV PANATAANPH_DB_PATH=/app/data/panataanph.db
ENV PANATAANPH_STORAGE_PATH=/app/storage
ENV PORT=8000

EXPOSE 8000

CMD ["sh", "-c", "uvicorn backend.main:app --app-dir src --host 0.0.0.0 --port ${PORT:-8000}"]
