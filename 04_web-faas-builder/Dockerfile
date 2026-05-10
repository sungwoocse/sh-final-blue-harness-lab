# =============================================================================
# Multi-stage Dockerfile for Spin K8s Deployment Tool
# Supports IRSA (IAM Roles for Service Accounts) for AWS authentication
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Builder - Install dependencies and prepare the application
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install uv for faster dependency management
RUN pip install --no-cache-dir uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies using uv
RUN uv pip install --system --no-cache -r pyproject.toml

# Copy application source
COPY main.py ./
COPY src/ ./src/

# -----------------------------------------------------------------------------
# Stage 2: Spin Builder - Prepare Spin Python venv template
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS spin-builder

# Install curl for downloading spin
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \ 
    && rm -rf /var/lib/apt/lists/*

# Install Spin CLI by directly downloading the binary (skip template installation)
ARG SPIN_VERSION=v3.5.1
RUN curl -fsSL "https://github.com/spinframework/spin/releases/download/${SPIN_VERSION}/spin-${SPIN_VERSION}-linux-amd64.tar.gz" -o spin.tar.gz && \
    tar -xzf spin.tar.gz && \
    mv spin /usr/local/bin/ && \
    rm -rf spin.tar.gz *.pem *.sig README.md LICENSE

# Install spin kube plugin for scaffold command (in spin-builder stage)
# Set SPIN_HOME explicitly to ensure consistent plugin location
# Disable telemetry to avoid otel initialization errors in CI
ENV SPIN_HOME=/opt/spin
ENV OTEL_SDK_DISABLED=true
RUN mkdir -p /opt/spin && \
    /usr/local/bin/spin plugins install --url https://github.com/spinframework/spin-plugin-kube/releases/download/v0.4.0/kube.json --yes

# Create venv template with componentize-py and spin-sdk
# Pin versions for compatibility (componentize-py 0.17.2 works with spin-sdk 3.4.1)
RUN python3 -m venv /opt/spin-python-venv && \
    /opt/spin-python-venv/bin/pip install --upgrade pip && \
    /opt/spin-python-venv/bin/pip install componentize-py==0.17.2 spin-sdk==3.4.1

# -----------------------------------------------------------------------------
# Stage 3: Runtime - Final production image
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install kubectl for K8s operations
RUN curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" && \
    chmod +x kubectl && \
    mv kubectl /usr/local/bin/

# Copy Spin CLI from spin-builder
COPY --from=spin-builder /usr/local/bin/spin /usr/local/bin/spin

# Copy Spin plugins (kube) from spin-builder - pre-installed in builder stage
COPY --from=spin-builder /opt/spin /opt/spin

# Copy Spin Python venv template
COPY --from=spin-builder /opt/spin-python-venv /opt/spin-python-venv

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages

# Copy Python bin scripts (mypy, etc.) from builder
COPY --from=builder /usr/local/bin/mypy /usr/local/bin/mypy

# Copy application
COPY --from=builder /app /app

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app /opt/spin-python-venv /opt/spin

USER appuser

# Environment variables
# AWS credentials are provided via IRSA - no need to set AWS_ACCESS_KEY_ID/SECRET
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    # Spin home directory for plugins
    SPIN_HOME=/opt/spin \
    # Spin Python venv template path
    SPIN_PYTHON_VENV_TEMPLATE=/opt/spin-python-venv \
    # DynamoDB table name
    DYNAMODB_TABLE_NAME=sfbank-blue-FaaSData \
    # S3 bucket for build artifacts
    S3_BUCKET_NAME=sfbank-blue-functions-code-bucket \
    # Core Service endpoint (optional - uses mock if not set)
    CORE_SERVICE_ENDPOINT=""

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Run the application
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
