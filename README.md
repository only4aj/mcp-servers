# MCP Servers Collection

> **General:** This repository hosts a collection of Model Context Protocol (MCP) servers, each providing specific functionality through a standardized interface.
> All servers follow a consistent pattern and are implemented in Python with Server-Sent Events (SSE) transport.



## Key Features

- **Standardized Implementation**: All servers follow the pattern established in the template server
- **Python-Based**: Built with Python 3.12+ and modern language features
- **SSE Transport**: Exclusively uses Server-Sent Events for communication
- **Modular Design**: Each server is a self-contained module with its own configuration
- **Consistent Documentation**: Standardized README structure across all servers
- **Docker Support**: All servers include containerization support

## Available Servers

1. **MCP Template Server** (`mcp-server-template/`)
   - Base template for creating new MCP servers
   - Includes calculator functionality as an example
   - Reference implementation for all other servers

2. **MCP YouTube Server** (`mcp-server-youtube/`)
   - YouTube video search and transcript retrieval
   - Uses YouTube Data API v3 and transcript extraction

## Common Requirements

All servers share these base requirements:
- Python 3.12+
- Docker (optional, for containerization)
- Environment-based configuration
- Type hints and modern Python syntax

## Contributing

We welcome contributions of new MCP servers! Please follow these guidelines:

1. **Use the Template**: Start with `mcp-server-template/` as your base
2. **Follow the Pattern**: Maintain the established project structure
3. **Documentation**: Include a comprehensive README following the template format
4. **Testing**: Provide example usage and test cases
5. **Type Safety**: Use type hints throughout the code
6. **Modern Python**: Utilize Python 3.12+ features
7. **Environment Config**: No hardcoded values, use environment variables
8. **Docker Support**: Include Dockerfile and docker-compose if needed

### Adding a New Server

1. Copy the template server:
   ```bash
   cp -r mcp-server-template mcp-server-your-service
   ```

2. Update the following:
   - README.md with your service details
   - pyproject.toml with your dependencies
   - Implementation in src/
   - Environment variables in .env.example

3. Submit a pull request with your new server

## Project Structure

Each server follows this structure:
```
mcp-server-{name}/
├── src/
│   └── mcp_server_{name}/
│       └── {name}/
│           ├── __init__.py
│           ├── config.py
│           ├── module.py
│       ├── __init__.py
│       ├── __main__.py
│       ├── logging_config.py
│       ├── server.py
├── .env.example
├── .gitignore
├── Dockerfile
├── LICENSE
├── pyproject.toml
├── README.md
└── dependency.lock
```

## License

MIT