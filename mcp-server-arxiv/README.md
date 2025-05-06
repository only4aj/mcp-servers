# MCP Server - Arxiv Search

This service provides an MCP-compliant server interface with a tool to search and retrieve papers from the [Arxiv](https://arxiv.org/) preprint repository.

## Features

- Provides an MCP tool (`arxiv_search`) for searching academic papers
- Uses the `arxiv` Python library for interaction with the Arxiv API
- Configurable via environment variables (search parameters, result limits)
- Follows the `mcp-servers` structure and patterns
- Supports SSE transport via Starlette/Uvicorn
- Includes Docker support

## Requirements

- Python 3.11+
- No API key required (Arxiv is free to use)

## Setup

1. **Clone the Repository:** Ensure this directory is within your `mcp-servers` project or clone it standalone.
2. **Create Environment File:**
   Create a `.env` file in this directory (`mcp-server-arxiv`) based on `.env.example`. You can optionally configure search parameters and server settings.
3. **Install Dependencies:**
   It's recommended to use a virtual environment. Navigate to the `mcp-server-arxiv` directory.

   ```bash
   # Using uv (recommended)
   uv venv
   source .venv/bin/activate  # or .venv\Scripts\activate on Windows
   uv pip install -e .[dev] # Install in editable mode with dev tools

   # Using pip + venv
   # python -m venv .venv
   # source .venv/bin/activate # or .venv\Scripts\activate on Windows
   # pip install -e .[dev]
   ```

## Running the Server

Ensure your virtual environment is activated and the `.env` file is present and configured.

```bash
# Run with default host (0.0.0.0) and port (8004)
python -m mcp_server_arxiv

# Run on a specific host/port
python -m mcp_server_arxiv --host 127.0.0.1 --port 8004
```

### Docker Support

```bash
# Build the Docker image
docker build -t mcp-server-arxiv .

# Run the container
docker run --rm -it -p 8006:8006 --env-file .env mcp-server-arxiv
```

## API Usage

The server provides the following MCP tool:

- `arxiv_search`: Search for academic papers on Arxiv
  - Parameters:
    - `query`: Search query string
    - `max_results`: Maximum number of results to return (default: 5)
    - `sort_by`: Sort order ('relevance' or 'lastUpdatedDate')
    - `sort_order`: Sort direction ('descending' or 'ascending')

## Development

The project uses:
- `uv` for dependency management
- `pytest` for testing
- `black` and `isort` for code formatting
- `mypy` for type checking

Run tests with:
```bash
pytest
```

Format code with:
```bash
black .
isort .
```