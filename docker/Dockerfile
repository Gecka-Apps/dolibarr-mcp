# Multi-stage Docker build for Dolibarr MCP Server
FROM python:3.12-slim AS builder

# Dependency resolution is pinned to uv.lock, so the image ships the exact
# versions the test-suite runs against.
COPY --from=ghcr.io/astral-sh/uv:0.9.27 /uv /uvx /bin/

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create working directory
WORKDIR /app

# Third-party dependencies first, so a source-only change keeps this layer
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --extra analytics

# Copy source code
COPY src/ ./src/
COPY README.md LICENSE ./

# Install the package itself into the same environment
RUN uv sync --frozen --extra analytics

# Production stage
FROM python:3.12-slim AS production

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

# Create non-root user
RUN groupadd -r dolibarr && useradd -r -g dolibarr dolibarr

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# The project is installed in editable mode, so the environment and the sources
# it points at must land on the same paths as in the builder.
COPY --from=builder /app/.venv/ /app/.venv/
COPY --from=builder /app/src/ /app/src/

# Create working directory and set ownership
WORKDIR /app
RUN chown -R dolibarr:dolibarr /app

# Switch to non-root user
USER dolibarr

# Health check using test command
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -m dolibarr_mcp.test_connection || exit 1

# Expose port (for HTTP interface)
EXPOSE 8080

# Default command runs the MCP server
CMD ["python", "-m", "dolibarr_mcp.dolibarr_mcp_server"]

# Labels for metadata
LABEL org.opencontainers.image.title="Dolibarr MCP Server" \
      org.opencontainers.image.description="Model Context Protocol server for Dolibarr ERP with analytics" \
      org.opencontainers.image.url="https://github.com/Gecka-Apps/dolibarr-mcp" \
      org.opencontainers.image.source="https://github.com/Gecka-Apps/dolibarr-mcp" \
      org.opencontainers.image.version="1.2.0" \
      org.opencontainers.image.licenses="MIT"
