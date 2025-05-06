# Use a Python image with uv pre-installed
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim as builder

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Copy project files needed for dependency installation
COPY pyproject.toml ./
# COPY uv.lock ./ # Uncomment if you use uv.lock

# Install dependencies only
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-install-project --no-dev --no-editable

# Copy the rest of the application code
COPY . /app

# Install the project itself
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev --no-editable

# Production stage
FROM python:3.12-slim-bookworm as prod

WORKDIR /app

# Copy only the installed virtual environment
COPY --from=builder /app/.venv /app/.venv
# Copy only the source code needed for runtime
COPY --from=builder /app/src /app/src

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
# Ensure src is in PYTHONPATH
ENV PYTHONPATH="/app/src"

# Default port
ENV MCP_ARXIV_PORT=8006
# Ensure the server binds to all interfaces
ENV MCP_ARXIV_HOST="0.0.0.0"
EXPOSE 8006

# Explicitly bind to all interfaces for container networking
ENTRYPOINT ["python", "-m", "mcp_server_arxiv", "--host", "0.0.0.0"]
