# ATC Backend Dockerfile
# FastAPI application with hot-reload support for development

FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency management
RUN pip install --no-cache-dir uv

# Copy dependency files first for better caching
COPY pyproject.toml .

# Install dependencies
RUN uv pip install --system -e ".[dev]"

# Copy application code
# Note: In development, this is overridden by volume mount
COPY . .

# Default command (overridden in docker-compose for development)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
