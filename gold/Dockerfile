# Aurum Terminal — image production (frontend build sẵn + backend FastAPI).
# Build từ thư mục gold/:  docker build -t aurum-terminal:1.0 .
# Chạy:                    docker compose up -d

# ---------- stage 1: build frontend ----------
FROM node:20-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ---------- stage 2: backend ----------
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
RUN useradd -m appuser
WORKDIR /app/backend
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
COPY --from=web /web/dist /app/frontend/dist
RUN mkdir -p /app/data /app/backups && chown -R appuser:appuser /app
USER appuser

ENV GOLD_HOST=0.0.0.0 \
    GOLD_PORT=8000 \
    GOLD_DB_PATH=/app/data/gold.db
EXPOSE 8000
HEALTHCHECK --interval=60s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=5)"
CMD ["python", "run.py"]
