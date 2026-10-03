# Stage 1: Build environment
FROM python:3.11-slim-bookworm AS builder

WORKDIR /app

# Install compilation tooling and postgres development libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies to system location
COPY src/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code into builder
COPY src/ ./src/

# Stage 2: Minimal runtime environment
FROM python:3.11-slim-bookworm

WORKDIR /app

# Install minimal runtime library for PostgreSQL
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Create dedicated non-root user and group for runtime security
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -m -s /sbin/nologin appuser

# Copy installed python dependencies and executables from builder stage
COPY --from=builder /usr/local /usr/local

# Copy application source code from builder stage
COPY --from=builder /app /app

# Configure permissions for non-root user
RUN chown -R appuser:appgroup /app

# Switch to unprivileged user
USER appuser

# Runtime environment settings
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

EXPOSE 8000

# Start API server
CMD ["python", "src/app.py"]
