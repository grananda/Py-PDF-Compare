# syntax=docker/dockerfile:1

# ============================================================
# PDF Compare - Container Image
# Compatible with: Docker, Podman, containerd, buildah, etc.
# ============================================================

# Build arguments for flexibility
ARG PYTHON_VERSION=3.12

# Base image
FROM python:${PYTHON_VERSION}-slim

# OCI Image Labels (standard metadata)
LABEL org.opencontainers.image.title="PDF Compare"
LABEL org.opencontainers.image.description="Compare two PDF files and generate a visual diff report"
LABEL org.opencontainers.image.source="https://github.com/grananda/PDF-Compare"
LABEL org.opencontainers.image.licenses="MIT"

# Create non-root user for security
ARG UID=1000
ARG GID=1000
RUN groupadd --gid ${GID} appuser \
    && useradd --uid ${UID} --gid ${GID} --create-home --shell /bin/bash appuser

# Set working directory
WORKDIR /app

# Environment configuration
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/home/appuser/.local/bin:$PATH"

# Install system dependencies
# - poppler-utils: Required for pdf2image
# - curl: Required to install uv and health checks
# - ca-certificates: Required for HTTPS
RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Switch to non-root user
USER appuser

# Install uv as non-root user
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Copy dependency files first (for better layer caching)
COPY --chown=appuser:appuser pyproject.toml uv.lock ./

# Install Python dependencies
RUN uv sync --frozen --no-dev

# Copy application code
COPY --chown=appuser:appuser . .

# Default command (can be overridden)
ENTRYPOINT ["uv", "run", "python", "compare_pdf.py"]

# Health check for API mode (ignored in CLI mode)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -sf http://localhost:5000/health || exit 1
