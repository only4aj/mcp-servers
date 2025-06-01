import logging
from enum import StrEnum
from typing import AsyncIterator, List, Dict, Any, Optional
from contextlib import asynccontextmanager
from mcp.server import Server
from mcp.types import Tool, TextContent
from pydantic import BaseModel, Field, ValidationError

from mcp_server_tavily.tavily import (
    _TavilyService, 
    get_tavily_service,
    TavilyServiceError,
    TavilySearchResult,
)

logger = logging.getLogger(__name__)

# --- Tool Constants & Enums --- #
class TavilyToolNames(StrEnum):
    """Enum for Tavily MCP tool names."""

    WEB_SEARCH = "tavily_web_search"

# --- Tool Input/Output Schemas --- #
class TavilySearchRequest(BaseModel):
    """Input schema for the tavily_web_search tool."""

    query: str = Field(..., description="The search query string for Tavily.")
    max_results: Optional[int] = Field(
        default=None,
        description="Optional override for the maximum number of search results.",
        ge=1
    )


# --- MCP Server Initialization --- #
@asynccontextmanager
async def server_lifespan(server: Server) -> AsyncIterator[Dict[str, Any]]:
    """
    Manage MCP server startup/shutdown. Initializes the Tavily service.
    """
    logger.info("MCP Lifespan: Initializing Tavily service...")
    context = {}

    try:
        tavily_service = get_tavily_service()
        context["tavily_service"] = tavily_service

        logger.info("MCP Lifespan: Tavily service initialized successfully.")
        yield context
    except TavilyServiceError as e:
        logger.error(f"FATAL: MCP Lifespan initialization failed: {e}", exc_info=True)
        raise
    except Exception as e:
        logger.error(f"FATAL: Unexpected error during MCP Lifespan initialization: {e}", exc_info=True)
        raise
    finally:
        logger.info("MCP Lifespan: Shutdown.")



server = Server("tavily-mcp-server", lifespan=server_lifespan)


# --- Tool Definitions --- #


@server.list_tools()
async def list_tools() -> list[Tool]:
    """Lists the tools available in this MCP server."""
    logger.debug("Listing available tools.")

    return [
        Tool(
            name=TavilyToolNames.WEB_SEARCH.value,
            description="Performs a web search using the Tavily API based on the provided query.",
            inputSchema=TavilySearchRequest.model_json_schema(),
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handles incoming tool calls for the Tavily MCP server."""
    logger.info(f"Received call_tool request for '{name}' with args: {arguments}")

    # Retrieve the service instance from lifespan context
    tavily_service: _TavilyService = server.request_context.lifespan_context["tavily_service"]

    # --- Tool Business Logic --- #
    match name:
        case TavilyToolNames.WEB_SEARCH.value:
        
            try:
                # 1. Validate Input 
                request_model = TavilySearchRequest(**arguments)
                
                # 2. Execute Core Logic using the service
                search_results: List[TavilySearchResult] = await tavily_service.search(
                    query=request_model.query,
                    max_results=request_model.max_results 
                )
                
                formatted_response = "\n\n".join([str(result) for result in search_results])
                return [TextContent(type="text", text=formatted_response)]

            except ValidationError as ve:
                error_msg = f"Invalid arguments for tool '{name}': {ve}"
                logger.warning(error_msg)
                return [TextContent(type="text", text=error_msg)]

            except ValueError as val_err: 
                error_msg = f"Input validation error for tool '{name}': {val_err}"
                logger.warning(error_msg)
                return [TextContent(type="text", text=error_msg)]

            except TavilyServiceError as client_err:
                error_msg = f"Tavily client error processing tool '{name}': {client_err}"
                logger.error(error_msg, exc_info=True)
                return [TextContent(type="text", text=error_msg)]

            except Exception as e:
                error_msg = f"An unexpected internal error occurred processing tool '{name}'."
                logger.error(f"{error_msg} Details: {e}", exc_info=True)
                return [TextContent(type="text", text=error_msg)]

        case _:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]