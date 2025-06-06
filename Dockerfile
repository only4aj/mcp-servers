# Base builder with common dependencies
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS base-builder

WORKDIR /app

# Создаём виртуальное окружение
RUN uv venv /app/.venv --python python3.12

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV PATH="/app/.venv/bin:$PATH"

# --- Copy and install each independent service --- #

COPY ./mcp-server-youtube /app/mcp-server-youtube
RUN uv pip install /app/mcp-server-youtube

COPY ./mcp-server-tavily /app/mcp-server-tavily
RUN uv pip install /app/mcp-server-tavily

COPY ./mcp-server-arxiv /app/mcp-server-arxiv
RUN uv pip install /app/mcp-server-arxiv

COPY ./mcp-server-imgen /app/mcp-server-imgen
RUN uv pip install /app/mcp-server-imgen

COPY ./mcp-server-stability /app/mcp-server-stability
RUN uv pip install /app/mcp-server-stability

COPY ./mcp-server-qdrant /app/mcp-server-qdrant
RUN uv pip install /app/mcp-server-qdrant

COPY ./mcp-server-telegram /app/mcp-server-telegram
RUN uv pip install /app/mcp-server-telegram

COPY ./mcp-server-twitter /app/mcp-server-twitter
RUN uv pip install /app/mcp-server-twitter


# Final stage: minimal runtime image
FROM python:3.12-slim-bookworm AS prod

WORKDIR /app

# Copy virtual environment from builder
COPY --from=base-builder /app/.venv /app/.venv

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1


CMD ["tail", "-f", "/dev/null"]
