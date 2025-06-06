# MCP Servers - Unified Runner

This repository contains multiple [MCP (Model Context Protocol)](https://example.com/link-to-mcp-docs) server implementations.
It provides a unified Docker environment to build and run any of the contained servers.

Currently supported servers:

*   **imgen**: Generates images from text prompts using Google Vertex AI.
*   **qdrant**: Retrieves context from a Qdrant vector database.
*   **telegram**: Posts messages to a Telegram channel via a single API tool.
*   **youtube**: Retrieves transcripts of videos.
*   **twitter**: Interacts with Twitter/X API for posting tweets, following users, and retrieving user tweets.
*   **tavily**: Performs web searches using the Tavily search API.
*   **arxiv**: Searches and retrieves academic papers from arXiv.
*   **stability**: Generates images using Stability AI's SDXL models.

## Structure

*   `/`: Contains the unified Dockerfile, docker-compose files, consolidated configuration (`pyproject.toml`, `.env.example`), and this README.
*   `/mcp-server-imgen`: Contains the source code and specific files for the Image Generation server.
*   `/mcp-server-qdrant`: Contains the source code and specific files for the Qdrant server.
*   `/mcp-server-telegram`: Contains the source code and specific files for the Telegram server.
*   `/mcp-server-youtube`: Contains the source code and specific files for the YouTube transcript server.
*   `/mcp-server-twitter`: Contains the source code and specific files for the Twitter server.
*   `/mcp-server-tavily`: Contains the source code and specific files for the Tavily search server.
*   `/mcp-server-arxiv`: Contains the source code and specific files for the arXiv server.
*   `/mcp-server-stability`: Contains the source code and specific files for the Stability AI server.

## Getting Started

### Prerequisites

*   Docker
*   `uv` (optional, for local development/dependency management if not using Docker exclusively)

### Building the Unified Docker Image

From the root directory of this repository (`mcp-servers/`), run:

```bash
docker build -t mcp-server-unified .
```

This command builds a single Docker image tagged `mcp-server-unified` containing the code and dependencies for all supported servers.

### Running a Specific Server

You select which server to run by overriding the container's CMD to launch the specific module directly.

**Example - Running the Stability AI Server:**

```bash
docker run --rm -it \
  -p 8003:8000 \
  --env-file .env \
  mcp-server-unified \
  python -m mcp_server_stability
```

**Note:** Make sure to create a `.env` file in the root directory containing the necessary credentials for your chosen service (based on `.env.example`).

The service will be available on `http://localhost:8003`.

## Development

While the primary way to run the servers is via the unified Docker container, you can still develop the individual services locally.

*   Ensure you have `uv` installed.
*   It's recommended to manage dependencies using the top-level `pyproject.toml` and `uv.lock` to maintain consistency with the Docker build.
*   You can potentially create separate virtual environments for each service if needed, but sync them from the root `uv.lock`.

## Contributing

(Add contribution guidelines here)


