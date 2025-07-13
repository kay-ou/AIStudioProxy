# AIStudioProxy Dockerfile
# Multi-stage build for optimized production image

# Build stage
FROM python:3.11-slim as builder

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry

# Set work directory
WORKDIR /app

# Copy poetry files
COPY pyproject.toml poetry.lock* ./

# Configure poetry
RUN poetry config virtualenvs.create false

# Install Python dependencies
RUN poetry install --only=main --no-dev

# Production stage
FROM python:3.11-slim as production

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

# Install system dependencies for runtime
RUN apt-get update && apt-get install -y \
    # Browser dependencies
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libxss1 \
    libxtst6 \
    xdg-utils \
    # Process management
    supervisor \
    # Cleanup
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r aistudio && useradd -r -g aistudio -s /bin/bash aistudio

# Set work directory
WORKDIR /app

# Copy Python dependencies from builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Install Playwright and browsers
RUN pip install playwright
RUN playwright install chromium
RUN playwright install-deps chromium

# Create necessary directories
RUN mkdir -p /app/logs /app/auth /app/profiles /app/tmp && \
    chown -R aistudio:aistudio /app

# Copy application code
COPY --chown=aistudio:aistudio src/ src/
COPY --chown=aistudio:aistudio configs/ configs/
COPY --chown=aistudio:aistudio scripts/ scripts/

# Copy supervisor configuration
COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Make scripts executable
RUN chmod +x scripts/*.sh

# Switch to non-root user
USER aistudio

# Expose ports
EXPOSE 2048 9090

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:2048/health || exit 1

# Default command
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]

# Development stage
FROM production as development

# Switch back to root for development setup
USER root

# Install development dependencies
RUN pip install poetry
COPY pyproject.toml poetry.lock* ./
RUN poetry config virtualenvs.create false && \
    poetry install --with dev

# Install additional development tools
RUN apt-get update && apt-get install -y \
    vim \
    htop \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Switch back to non-root user
USER aistudio

# Override command for development
CMD ["python", "-m", "aistudioproxy.main", "--reload", "--debug"]
