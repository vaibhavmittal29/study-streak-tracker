# Lightweight Python 3.11 base image
FROM python:3.11-slim

# Prevent Python from writing .pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install runtime dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code, assets, and scripts
COPY app/ app/
COPY scripts/ scripts/

# Create data directory for SQLite persistence and set non-root user
RUN mkdir -p /app/data && \
    useradd -u 1000 -m appuser && \
    chown -R appuser:appuser /app

USER appuser

# Expose default HTTP application port
EXPOSE 8000

# Run uvicorn server respecting dynamic PORT environment variable (e.g. Render, Railway, Cloud Run)
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
