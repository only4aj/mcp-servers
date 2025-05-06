# --- Standard Library Imports ---
from __future__ import annotations
import logging
from enum import StrEnum
from typing import AsyncIterator, List, Dict, Any, Optional
from contextlib import asynccontextmanager

# --- Third-party Imports ---
from mcp.server import Server
from mcp.types import Tool, TextContent
from pydantic import BaseModel, Field, ValidationError

# --- Local Imports ---
from mcp_server_arxiv.arxiv_client import (
    ArxivService,
    get_arxiv_service,
    ArxivConfigError,
    ArxivClientError,
    ArxivApiError,
    ArxivResultDict,
)

# --- Logging Setup ---
logger = logging.getLogger(__name__)

# --- Tool Constants & Enums ---
class ArxivToolNames(StrEnum):
    """Enum for ArXiv MCP tool names."""
    ARXIV_SEARCH = "arxiv_search" 

# --- Tool Input/Output Schemas ---
class ArxivSearchRequest(BaseModel):
    """Input schema for the arxiv_search tool."""
    query: str = Field(..., description="The search query string for ArXiv.")
    max_results: Optional[int] = Field(
        default=None, 
        description="Optional override for the maximum number of results to process.",
        ge=1,
        le=50 
    )
    max_text_length: Optional[int] = Field(
        default=None, 
        description="Optional max characters of full text per paper. If null/omitted, uses server default or no limit.",
        ge=100
    )

# --- Lifespan Management for MCP Server ---
@asynccontextmanager
async def server_lifespan(server_instance: Server) -> AsyncIterator[Dict[str, Any]]:
    """Manage MCP server startup/shutdown. Initializes the ArXiv service."""
    logger.info("MCP Lifespan: Initializing ArXiv service...")
    try:
        arxiv_service = await get_arxiv_service() 
        logger.info("MCP Lifespan: ArXiv service initialized successfully.")
        yield {"arxiv_service": arxiv_service}
    except (ArxivConfigError, ArxivClientError) as e:
        logger.error(f"FATAL: MCP Lifespan initialization failed: {e}", exc_info=True)
        raise 
    except Exception as e:
        logger.error(f"FATAL: Unexpected error during MCP Lifespan initialization: {e}", exc_info=True)
        raise
    finally:
        logger.info("MCP Lifespan: Shutdown.")

# --- MCP Server Initialization ---
server = Server("arxiv-mcp-server", lifespan=server_lifespan)

# --- Tool Definitions ---
@server.list_tools()
async def list_tools() -> list[Tool]:
    """Lists the tools available in this MCP server."""
    try:
        await get_arxiv_service()
        logger.debug("Listing available tools: ArXiv service seems available.")
        return [
            Tool(
                name=ArxivToolNames.ARXIV_SEARCH.value,
                description="Searches arXiv for scientific papers based on a query, downloads PDFs, extracts text, and returns formatted results.",
                inputSchema=ArxivSearchRequest.model_json_schema(),
            )
        ]
    except (ArxivConfigError, ArxivClientError):
         logger.warning("ArXiv service unavailable during list_tools due to initialization error.")
         return []

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handles incoming tool calls for the ArXiv MCP server."""
    logger.info(f"Received call_tool request for '{name}' with args: {arguments}")

    # Check tool name
    if name != ArxivToolNames.ARXIV_SEARCH.value:
        logger.warning(f"Received call for unknown tool: {name}")
        return [TextContent(type="text", text=f"Unknown tool: {name}")]

    try:
        arxiv_service: ArxivService = server.request_context.lifespan_context["arxiv_service"]
    except KeyError:
        error_msg = "Server Internal Error: ArXiv service not found in context."
        logger.error(error_msg)
        return [TextContent(type="text", text=error_msg)]
    except Exception as ctx_err:
        error_msg = f"Server Internal Error: Failed to retrieve ArXiv service from context: {ctx_err}"
        logger.error(error_msg, exc_info=True)
        return [TextContent(type="text", text=error_msg)]

    # --- Handle arxiv_search ---
    try:
        # 1. Validate Input Arguments
        request_model = ArxivSearchRequest(**arguments)
        logger.info(f"Validated request for query: '{request_model.query}'")

        # 2. Execute Core Logic using the service
        search_results: List[ArxivResultDict] = await arxiv_service.search(
            query=request_model.query,
            max_results_override=request_model.max_results,
            max_text_length_override=request_model.max_text_length
        )

        # 3. Format Success Response
        formatted_response = arxiv_service.format_results(search_results)
        logger.info(f"Successfully processed '{name}' request. Returning formatted results.")
        logger.debug(f"Formatted response preview: {formatted_response[:500]}...")
        return [TextContent(type="text", text=formatted_response)]

    except ValidationError as ve:
        error_msg = f"Invalid arguments for tool '{name}': {ve}"
        logger.warning(error_msg)
        return [TextContent(type="text", text=error_msg)]
    except ValueError as val_err: 
         error_msg = f"Input validation error for tool '{name}': {val_err}"
         logger.warning(error_msg)
         return [TextContent(type="text", text=error_msg)]
    except ArxivApiError as api_err:
        error_msg = f"ArXiv API/processing error for tool '{name}': {api_err}"
        logger.error(error_msg, exc_info=True)
        return [TextContent(type="text", text=error_msg)]
    except ArxivClientError as client_err:
        error_msg = f"ArXiv client error processing tool '{name}': {client_err}"
        logger.error(error_msg, exc_info=True)
        return [TextContent(type="text", text=error_msg)]
    except Exception as e:
        error_msg = f"An unexpected internal error occurred processing tool '{name}'."
        logger.error(f"{error_msg} Details: {e}", exc_info=True)
        return [TextContent(type="text", text=error_msg)]