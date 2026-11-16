# Stage 1: Build Frontend
FROM node:20-slim AS frontend-build
WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# Stage 2: Runtime Environment
FROM python:3.12-slim AS runtime
WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DATA_DIR=/var/data \
    PORT=8000 \
    ENVIRONMENT=production

# Install system dependencies (build-essential, curl for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements and install
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy backend source code and scripts
COPY backend/ ./backend/
COPY scripts/ ./scripts/

# Copy built frontend assets from stage 1
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

# Ensure persistent mount directory exists
RUN mkdir -p /var/data && chmod 777 /var/data

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Start server: runs migrations & seeds on startup via lifespan, binding 0.0.0.0:$PORT
CMD ["sh", "-c", "PYTHONPATH=. uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT}"]
