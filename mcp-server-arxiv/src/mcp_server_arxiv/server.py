from __future__ import annotations
import logging
from enum import StrEnum
from typing import AsyncIterator, List, Dict, Any, Optional
from contextlib import asynccontextmanager

from mcp.server import Server
from mcp.types import Tool, TextContent
from pydantic import BaseModel, Field, ValidationError

from mcp_server_arxiv.arxiv import (
    _ArxivService,
    get_arxiv_service,
    ArxivServiceError,
    ArxivConfigError,
    ArxivApiError,
    ArxivSearchResult,
)

logger = logging.getLogger(__name__)

# --- Tool Constants & Enums ---\nclass ArxivToolNames(StrEnum):
class ArxivToolNames(StrEnum):
    """Enum for ArXiv MCP tool names."""
    ARXIV_SEARCH = "arxiv_search"

# --- Tool Input Schema --- #
class ArxivSearchRequest(BaseModel):
    """Input schema for the arxiv_search tool."""
    query: str = Field(..., description="The search query string for ArXiv.")
    max_results: Optional[int] = Field(
        default=None,
        description="Optional override for the maximum number of results to fetch and process.",
        ge=1,
        le=50 # Sensible upper limit for a single call, aligned with config
    )
    max_text_length: Optional[int] = Field(
        default=None,
        description="Optional max characters of full text per paper. If null/omitted, uses server default or no limit.",
        ge=100
    )

# --- Lifespan Management for MCP Server --- #
@asynccontextmanager
async def server_lifespan(server_instance: Server) -> AsyncIterator[Dict[str, Any]]:
    """
    Manage MCP server startup/shutdown. Initializes the ArXiv service.
    """
    logger.info("MCP Lifespan (ArXiv): Initializing ArXiv service...")
    context = {}
    try:
        arxiv_service = get_arxiv_service()
        context["arxiv_service"] = arxiv_service
        logger.info("MCP Lifespan (ArXiv): ArXiv service initialized successfully.")
        yield context 
    except (ArxivConfigError, ArxivServiceError) as e: 
        logger.error(f"FATAL: MCP Lifespan (ArXiv) initialization failed: {e}", exc_info=True)
        raise RuntimeError(f"Failed to initialize ArXiv service: {e}") from e
    except Exception as e:
        logger.error(f"FATAL: Unexpected error during MCP Lifespan (ArXiv) initialization: {e}", exc_info=True)
        raise RuntimeError(f"Unexpected error during ArXiv service initialization: {e}") from e
    finally:
        logger.info("MCP Lifespan (ArXiv): Shutdown.")

# --- MCP Server Initialization --- #
server = Server(
    name="arxiv-mcp-server",
    lifespan=server_lifespan 
)

# --- Tool Definitions --- #
@server.list_tools()
async def list_tools() -> list[Tool]:
    """Lists the tools available in this MCP server."""
    logger.debug("Listing available tools for ArXiv MCP server.")
    return [
        Tool(
            name=ArxivToolNames.ARXIV_SEARCH.value,
            description="Searches arXiv for scientific papers based on a query, downloads PDFs, extracts text, and returns formatted results.",
            inputSchema=ArxivSearchRequest.model_json_schema(),
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handles incoming tool calls for the ArXiv MCP server."""
    logger.info(f"Received call_tool request for '{name}' with args: {arguments}")

    # Check tool name
    if name != ArxivToolNames.ARXIV_SEARCH.value:
        logger.warning(f"Received call for unknown tool: {name}")
        available_tools_names = [t.name for t in await list_tools()]
        return [TextContent(type="text", text=f"Error: Unknown tool '{name}'. Available tools: {available_tools_names}")]

    # Retrieve the service instance from lifespan context
    try:
        arxiv_service: _ArxivService = server.request_context.lifespan_context["arxiv_service"]
    except KeyError:
        error_msg = "Server Internal Error: ArXiv service not found in request context. Initialization might have failed."
        logger.error(error_msg)
        return [TextContent(type="text", text=error_msg)]
    except Exception as ctx_err: # Catch any other error during context access
        error_msg = f"Server Internal Error: Failed to retrieve ArXiv service from context: {ctx_err}"
        logger.error(error_msg, exc_info=True)
        return [TextContent(type="text", text=error_msg)]

    # --- Handle arxiv_search --- #
    try:
        # 1. Validate Input Arguments using Pydantic model
        request_model = ArxivSearchRequest(**arguments)
        logger.info(f"Validated request for ArXiv search: query='{request_model.query}', max_results={request_model.max_results}, max_text_length={request_model.max_text_length}")

        # 2. Execute Core Logic using the service
        search_results: List[ArxivSearchResult] = await arxiv_service.search(
            query=request_model.query,
            max_results_override=request_model.max_results,
            max_text_length_override=request_model.max_text_length
        )

        # 3. Format Success Response
        if not search_results:
            formatted_response = "No relevant papers found or processed on arXiv for the given query."
        else:

            formatted_items = ["ArXiv Search Results:\n"]
            for i, result in enumerate(search_results):
                formatted_items.append(f"\n--- Paper {i+1} ---\n{str(result)}")
            formatted_response = "\n".join(formatted_items)

        logger.info(f"Successfully processed '{name}' request. Returning {len(search_results)} formatted ArXiv results.")
        if search_results: # Log preview only if there are results
             logger.debug(f"Formatted response preview (first 500 chars): {formatted_response[:500]}...")
        return [TextContent(type="text", text=formatted_response)]

    # --- Error Handling during Tool Execution --- #
    except ValidationError as ve:
        error_msg = f"Error: Invalid arguments provided for tool '{name}'. Details: {ve}"
        logger.warning(f"Validation Error for tool '{name}': {ve}") # ve already contains good details
        return [TextContent(type="text", text=error_msg)]

    except ValueError as val_err: # Catch specific value errors from service (e.g., empty query)
         error_msg = f"Error: Input validation failed for tool '{name}'. Details: {val_err}"
         logger.warning(error_msg) # val_err is already descriptive
         return [TextContent(type="text", text=error_msg)]

    except ArxivApiError as api_err:
        error_msg = f"Error: An issue occurred while interacting with the ArXiv API or processing results for tool '{name}'. Details: {api_err}"
        logger.error(f"ArXiv API Error for tool '{name}' (Query: '{arguments.get('query', 'N/A')}'): {api_err}", exc_info=True)
        return [TextContent(type="text", text=error_msg)]

    except ArxivServiceError as service_err: # Catch other service-level errors
        error_msg = f"Error: A problem occurred within the ArXiv service while processing tool '{name}'. Details: {service_err}"
        logger.error(f"ArXiv Service Error for tool '{name}': {service_err}", exc_info=True)
        return [TextContent(type="text", text=error_msg)]

    except Exception as e:
        # Catch-all for unexpected errors during tool execution
        error_msg = f"Error: An unexpected internal error occurred while processing tool '{name}'. Please check server logs for details."
        logger.error(f"Unexpected Internal Error processing tool '{name}': {e}", exc_info=True)
        return [TextContent(type="text", text=error_msg)]