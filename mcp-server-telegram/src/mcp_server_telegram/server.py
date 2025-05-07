# src/mcp_server_telegram/server.py

# --- Standard Library Imports ---
from __future__ import annotations
import logging
import os
from enum import StrEnum

# --- Third-party Imports ---
from mcp.server import Server
from mcp.types import Tool, TextContent
from pydantic import BaseModel, Field

# --- Local Imports ---
from mcp_server_telegram.telegram_client import (
    send_msg_to_telegram,
    TelegramConfig,
    TelegramClientError,
    TelegramApiError
)

# --- Logging Setup ---
logging.basicConfig(level=os.getenv("MCP_TELEGRAM_LOG_LEVEL", "INFO").upper(), 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("telegram-mcp-server")

# --- Tool Constants & Enums ---
class TelegramToolNames(StrEnum):
    """Enum for Telegram MCP tool names."""
    POST_MESSAGE = "post_to_telegram"

# --- Tool Input/Output Schemas ---
class TelegramPostRequest(BaseModel):
    """Input schema for the post_to_telegram tool."""
    message: str = Field(..., description="The text message content to post to the Telegram channel.")

# --- MCP Server Initialization ---
server = Server("telegram-mcp-server")

# --- Global Config Object ---
# Will be initialized when server starts
telegram_config = None

def init_telegram_config():
    """Initialize Telegram configuration."""
    global telegram_config
    
    try:
        # Check required environment variables already verified in __main__.py
        telegram_config = TelegramConfig()
        logger.info("Telegram configuration loaded successfully")
        logger.info(f"Using Telegram channel: {telegram_config.channel}")
        
        # Log partial token for security
        if telegram_config.token:
            masked_token = '*' * (len(telegram_config.token) - 4) + telegram_config.token[-4:]
            logger.info(f"Using Telegram token ending with: {telegram_config.token[-4:]}")
            
        return True
        
    except ValueError as ve:
        logger.error(f"FATAL: {ve}")
        return False
        
    except Exception as e:
        logger.error(f"FATAL: Failed to load Telegram configuration: {e}", exc_info=True)
        return False

# --- Tool Definitions ---

@server.list_tools()
async def list_tools() -> list[Tool]:
    """Lists the tools available in this MCP server."""
    # Initialize config if not already done
    global telegram_config
    if telegram_config is None:
        if not init_telegram_config():
            logger.warning("Telegram tool unavailable because configuration failed to load")
            return []
    
    return [
        Tool(
            name=TelegramToolNames.POST_MESSAGE.value,
            description="Posts a given message to a pre-configured Telegram channel.",
            inputSchema=TelegramPostRequest.model_json_schema(),
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handles incoming tool calls for the Telegram MCP server."""
    logger.info(f"Received call_tool request for '{name}' with args: {arguments}")

    # --- Check if config loaded ---
    global telegram_config
    if telegram_config is None:
        if not init_telegram_config():
            error_msg = "Server Configuration Error: Telegram settings failed to load. Cannot execute tool."
            logger.error(error_msg)
            return [TextContent(type="text", text=error_msg)]

    # --- Validate Tool Name ---
    if name != TelegramToolNames.POST_MESSAGE.value:
        logger.warning(f"Received call for unknown tool: {name}")
        return [TextContent(type="text", text=f"Unknown tool: {name}")]

    # --- Handle post_to_telegram ---
    try:
        # Validate input arguments
        request_model = TelegramPostRequest(**arguments)
        logger.info(f"Validated request to post message: '{request_model.message[:50]}...'")

        # Execute core logic
        success = send_msg_to_telegram(telegram_config, request_model.message)

        # Format and return result
        if success:
            response_text = "Message successfully posted to the Telegram channel."
            logger.info(response_text)
        else:
            response_text = "Failed to post message to the Telegram channel. Check server logs for specific API errors."
            logger.warning(response_text)

        return [TextContent(type="text", text=response_text)]

    except ValueError as ve:
        error_msg = f"Invalid arguments for tool '{name}': {ve}"
        logger.warning(error_msg)
        return [TextContent(type="text", text=error_msg)]

    except TelegramClientError as client_err:
        error_msg = f"Telegram client error processing tool '{name}': {client_err}"
        logger.error(error_msg, exc_info=True)
        return [TextContent(type="text", text=error_msg)]

    except Exception as e:
        error_msg = f"An unexpected internal error occurred processing tool '{name}'."
        logger.error(f"{error_msg} Details: {e}", exc_info=True)
        return [TextContent(type="text", text=error_msg)]