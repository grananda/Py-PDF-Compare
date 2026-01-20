# syntax=docker/dockerfile:1

# ============================================================
# PDF Compare - Flask API Container (Production)
# Compatible with: Docker, Podman, containerd, buildah, etc.
# ============================================================

# Build arguments
ARG PYTHON_VERSION=3.12

# =========================
# Stage 1: Build
# =========================
FROM python:${PYTHON_VERSION}-slim AS builder

WORKDIR /app

# Install uv
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
    && curl -LsSf https://astral.sh/uv/install.sh | sh \
    && rm -rf /var/lib/apt/lists/*

ENV PATH="/root/.local/bin:$PATH"

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies to a virtual environment
RUN uv sync --frozen --no-dev \
    && uv pip install gunicorn

# =========================
# Stage 2: Production
# =========================
FROM python:${PYTHON_VERSION}-slim AS production

# OCI Image Labels
LABEL org.opencontainers.image.title="PDF Compare API"
LABEL org.opencontainers.image.description="REST API for comparing PDF files"
LABEL org.opencontainers.image.source="https://github.com/grananda/PDF-Compare"
LABEL org.opencontainers.image.licenses="MIT"
LABEL org.opencontainers.image.version="1.0.0"

# Create non-root user
ARG UID=1000
ARG GID=1000
RUN groupadd --gid ${GID} appuser \
    && useradd --uid ${UID} --gid ${GID} --create-home --shell /bin/bash appuser

WORKDIR /app

# Environment configuration
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PATH="/app/.venv/bin:$PATH" \
    # Application config
    PORT=5000 \
    HOST=0.0.0.0 \
    WORKERS=2 \
    THREADS=4 \
    TIMEOUT=120 \
    GRACEFUL_TIMEOUT=30 \
    KEEP_ALIVE=5 \
    MAX_REQUESTS=1000 \
    MAX_REQUESTS_JITTER=50 \
    # Security
    DEBUG=false

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils \
    curl \
    ca-certificates \
    tini \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* \
    && apt-get clean

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY --chown=appuser:appuser . .

# Remove unnecessary files
RUN rm -rf tests/ *.md sample-files/ .git/ .vscode/ .idea/ __pycache__/ \
    Containerfile Dockerfile api.Containerfile api.Dockerfile \
    pdf-compare.js package.json node_modules/ 2>/dev/null || true

# Create directory for temporary files
RUN mkdir -p /app/tmp && chown appuser:appuser /app/tmp
ENV TMPDIR=/app/tmp

# Switch to non-root user
USER appuser

# Expose API port
EXPOSE ${PORT}

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -sf http://localhost:${PORT}/health || exit 1

# Use tini as init system for proper signal handling
ENTRYPOINT ["/usr/bin/tini", "--"]

# Run gunicorn with production settings
CMD ["sh", "-c", "exec gunicorn \
    --bind ${HOST}:${PORT} \
    --workers ${WORKERS} \
    --threads ${THREADS} \
    --timeout ${TIMEOUT} \
    --graceful-timeout ${GRACEFUL_TIMEOUT} \
    --keep-alive ${KEEP_ALIVE} \
    --max-requests ${MAX_REQUESTS} \
    --max-requests-jitter ${MAX_REQUESTS_JITTER} \
    --access-logfile - \
    --error-logfile - \
    --capture-output \
    --enable-stdio-inheritance \
    api:app"]
