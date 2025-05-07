# MCP Telegram Server

MCP Server for Posting Messages to a Telegram Channel.

## Overview

This server provides an API with a single tool to send messages to a configured Telegram channel using a bot token.

## Features

- Post messages to a specific Telegram channel.
- Handles Telegram API interactions.
- API endpoint with structured JSON response.
- Docker support for easy deployment.

## Requirements

- Python 3.11+
- Telegram Bot Token
- Telegram Channel Username (e.g., `@mychannel`)

## Setup

1.  Clone the repository
2.  Create a `.env` file based on `.env.example` and add your Telegram Bot Token and Channel Username.
3.  Install the package:

## To run 
docker build -t mcp-server-telegram .
docker run --rm -it ` -p 8002:8002 ` --env-file .env ` mcp-server-telegram


```bash
# Make sure uv is installed or use pip
# pip install uv
uv pip install -e .
# Or with pip
# pip install -e '.[dev]' # Include dev dependencies
