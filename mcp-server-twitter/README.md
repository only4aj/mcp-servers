# MCP Twitter Server

> **General:** Twitter integration microservice implementing Model Context Protocol (MCP).

## Overview

This server provides Twitter functionality through MCP with the following features:
- Create tweets with media attachments and polls
- Retrieve user tweets
- Follow Twitter users

## MCP Tools

1. `create_tweet`
   - **Description:** Post a tweet with optional media and poll
   - **Input:**
     - text (string)
     - image_content (base64 string, optional)
     - poll_options (list of strings, 2-4 items)
     - poll_duration (integer, 5-10080 minutes)

2. `get_user_tweets`
   - **Description:** Retrieve recent tweets from a user
   - **Input:**
     - user_id (string)
     - max_results (integer, 1-100)

3. `follow_user`
   - **Description:** Follow a Twitter user
   - **Input:**
     - user_id (string)

## Requirements

- Python 3.12+
- Docker (optional)
- Twitter API credentials

## Setup

1. **Clone the Repository**:
   ```bash
   git clone <repository-url>
   cd mcp-server-template
   ```

2. **Create `.env` File based on `.env.example`**:
   ```dotenv
   # Example environment variables
   MCP_CALCULATOR_HOST="0.0.0.0"
   MCP_CALCULATOR_PORT=8000
   LOGGING_LEVEL="info"
   ```

3. **Install Dependencies**:
   ```bash
   uv sync .
   ```

## Running the Server

### Locally

```bash
# Basic run
python -m mcp_server_twitter

# Custom port and host
python -m mcp_server_twitter --host 0.0.0.0 --port 8008
```

### Using Docker

```bash
# Build the image
docker build -t mcp_server_twitter .
docker run -p 8008:8008 --env-file .env mcp_server_twitter
```

## Example Client
When server startup is completed, any MCP client
can utilize connection to it

```python
from mcp import Client

async with Client("http://localhost:8008/sse") as client:
    # Create tweet
    await client.call_tool("create_tweet", {
        "text": "Hello Twitter!",
        "image_content": "base64_image_data",
        "poll_options": ["Option 1", "Option 2"],
        "poll_duration": 1440
    })
    
    # Get user tweets
    tweets = await client.call_tool("get_user_tweets", {
        "user_id": "12345",
        "max_results": 10
    })
```

## Project Structure

```
mcp-server-twitter/
├── src/
│   └── mcp_server_twitter/
│       ├── twitter/          # Core Twitter logic
│       ├── __init__.py
│       ├── server.py         # MCP server setup
│       └── __main__.py       
├── .env.example
├── Dockerfile
├── pyproject.toml
└── README.md
```


## License

MIT
