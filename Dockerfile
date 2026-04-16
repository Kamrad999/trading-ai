# Multi-stage production Dockerfile for Trading AI
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN useradd --create-home --shell /bin/bash tradingai

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY docs/ ./docs/

# Create data directory with proper permissions
RUN mkdir -p /app/data && chown -R tradingai:tradingai /app

# Switch to non-root user
USER tradingai

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.path.insert(0, '/app/src'); from trading_ai.core.orchestrator import PipelineOrchestrator; print('OK')" || exit 1

# Expose port (if needed for web interface)
EXPOSE 8000

# Default command
CMD ["python", "-m", "trading_ai.cli", "run", "--dry-run"]
