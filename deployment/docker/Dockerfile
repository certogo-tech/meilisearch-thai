# Multi-stage Dockerfile for Thai tokenizer service
# Optimized for production with minimal size and fast startup

# Build stage - install dependencies and build wheels
FROM python:3.12-slim AS builder

# Install system dependencies needed for building Python packages
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip wheel && \
    pip install --no-cache-dir -r requirements.txt

# Production stage - minimal runtime image
FROM python:3.12-slim AS production

# Install only runtime system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy application code
COPY src/ ./src/
COPY pyproject.toml ./

# Create home directory and data directory for PyThaiNLP
# Also create directories for search proxy analytics and logs
RUN mkdir -p /home/appuser/.pythainlp && \
    mkdir -p /home/appuser/search-proxy/analytics && \
    mkdir -p /home/appuser/search-proxy/logs && \
    chown -R appuser:appuser /home/appuser && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Set PyThaiNLP data path
ENV PYTHAINLP_DATA_PATH=/home/appuser/.pythainlp

# Set search proxy paths
ENV SEARCH_PROXY_ANALYTICS_DIR=/home/appuser/search-proxy/analytics
ENV SEARCH_PROXY_LOG_DIR=/home/appuser/search-proxy/logs

# Health check configuration
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Environment variables for production
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Start command with optimized settings for performance
CMD ["uvicorn", "src.api.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "4", \
     "--access-log", \
     "--log-level", "info", \
     "--loop", "uvloop", \
     "--http", "httptools"]