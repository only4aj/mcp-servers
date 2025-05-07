# Use a Python image with uv pre-installed
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1

# Copy project files first
COPY . /app/

# Install dependencies and project
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev

# Final stage - minimal runtime image
FROM python:3.12-slim-bookworm

WORKDIR /app

# Copy only the installed virtual environment from the builder stage
COPY --from=builder /app/.venv /app/.venv
# Copy source code including the src directory
COPY --from=builder /app/src /app/src

# Add the venv bin to the PATH
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH="/app/src"
ENV MCP_TELEGRAM_PORT=8002

# Expose ports for the Telegram MCP server
EXPOSE 8002

# Run the server
CMD ["python", "-m", "mcp_server_telegram"]