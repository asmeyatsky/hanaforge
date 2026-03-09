# =============================================================================
# Stage 1: Build frontend
# =============================================================================
FROM node:20-alpine AS frontend-build

WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --ignore-scripts

COPY frontend/ ./
RUN npm run build

# =============================================================================
# Stage 2: Python runtime
# =============================================================================
FROM python:3.12-slim AS runtime

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd --gid 1001 hanaforge && \
    useradd --uid 1001 --gid hanaforge --shell /bin/bash --create-home hanaforge

# Install Python dependencies
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e . 2>/dev/null || pip install --no-cache-dir .

# Copy application source
COPY domain/ ./domain/
COPY application/ ./application/
COPY infrastructure/ ./infrastructure/
COPY presentation/ ./presentation/

# Re-install in editable mode now that source is present
RUN pip install --no-cache-dir -e .

# Copy built frontend static files
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

# Switch to non-root user
USER hanaforge

EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/api/v1/health || exit 1

# Run with uvicorn
CMD ["uvicorn", "presentation.api.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "2"]
