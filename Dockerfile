# Base builder with common dependencies
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS base-builder

WORKDIR /app
RUN uv venv /app/.venv --python python3.12
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# --- Independent service builds --- #
FROM base-builder AS youtube-builder
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=./mcp-server-youtube,target=/src \
    uv pip install /src

FROM base-builder AS tavily-builder  
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=./mcp-server-tavily,target=/src \
    uv pip install /src

FROM base-builder AS arxiv-builder
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=./mcp-server-arxiv,target=/src \
    uv pip install /src

FROM base-builder AS imgen-builder
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=./mcp-server-imgen,target=/src \
    uv pip install /src

FROM base-builder AS stability-builder
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=./mcp-server-stability,target=/src \
    uv pip install /src

FROM base-builder AS qdrant-builder
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=./mcp-server-qdrant,target=/src \
    uv pip install /src

FROM base-builder AS telegram-builder
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=./mcp-server-telegram,target=/src \
    uv pip install /src

FROM base-builder AS twitter-builder
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=./mcp-server-twitter,target=/src \
    uv pip install /src

# --- Final assembly stage --- #
FROM python:3.12-slim-bookworm AS prod

WORKDIR /app

# Copy base venv first
COPY --from=base-builder /app/.venv /app/.venv

# Copy each service 
COPY --from=youtube-builder /app/.venv /app/.venv
COPY --from=tavily-builder /app/.venv /app/.venv  
COPY --from=arxiv-builder /app/.venv /app/.venv
COPY --from=imgen-builder /app/.venv /app/.venv
COPY --from=stability-builder /app/.venv /app/.venv
COPY --from=qdrant-builder /app/.venv /app/.venv
COPY --from=telegram-builder /app/.venv /app/.venv
COPY --from=twitter-builder /app/.venv /app/.venv

ENV PATH="/app/.venv/bin:$PATH"

CMD ["tail", "-f", "/dev/null"]
