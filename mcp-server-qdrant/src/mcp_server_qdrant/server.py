"""
MCP server implementation for Qdrant vector database.
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from enum import StrEnum
    
from mcp.server import Server
from mcp.types import TextContent, Tool
from pydantic import BaseModel, Field, ValidationError

from mcp_server_qdrant.qdrant import (
    Entry, 
    QdrantConnector, 
    get_qdrant_connector
)

logger = logging.getLogger(__name__)

# --- Tool Input/Output Schemas --- #

class QdrantStoreRequest(BaseModel):
    """Input schema for the qdrant-store tool."""
    information: str = Field(..., description="The information to store.")
    collection_name: str = Field(..., description="The name of the collection to store the information in.")
    metadata: dict | None = Field(None, description="JSON metadata to store with the information, optional.")

class QdrantFindRequest(BaseModel):
    """Input schema for the qdrant-find tool."""
    query: str = Field(..., description="The query to use for the search.")
    collection_name: str = Field(..., description="The name of the collection to search in.")
    search_limit: int = Field(10, description="The maximum number of results to return.")

# --- Tool Name Enums --- #

class ToolNames(StrEnum):
    QDRANT_STORE = "qdrant-store"
    QDRANT_FIND = "qdrant-find"


# --- Lifespan Management for MCP Server --- #

@asynccontextmanager
async def server_lifespan(server: Server) -> AsyncIterator[dict]:
    """Manage server startup/shutdown. Initializes Qdrant services."""
    logger.info("Lifespan: Initializing Qdrant services...")
    context = {}

    try:
        # Initialize qdrant connector (singleton pattern)
        qdrant_connector = get_qdrant_connector()

        # Store in context
        context["qdrant_connector"] = qdrant_connector
        
        logger.info("Lifespan: Qdrant services initialized successfully.")
        yield context

    except Exception as init_err:
        logger.error(f"FATAL: Lifespan initialization failed: {init_err}", exc_info=True)
        raise init_err

    finally:
        logger.info("Lifespan: Shutdown cleanup.")

# --- MCP Server Initialization --- #

server = Server("qdrant-server", lifespan=server_lifespan)

# --- Tool Definitions --- #

@server.list_tools()
async def list_tools() -> list[Tool]:
    logger.debug("Listing available tools.")

    return [
        Tool(
            name=ToolNames.QDRANT_FIND.value,
            description="Look up memories in Qdrant. Use this tool when you need to: \n"
                        " - Find memories by their content \n"
                        " - Access memories for further analysis \n"
                        " - Get some personal information about the user",
            inputSchema=QdrantFindRequest.model_json_schema(),
        ),
        Tool(
            name=ToolNames.QDRANT_STORE.value,
            description= "Keep the memory for later use, when you are asked to remember something.",            
            inputSchema=QdrantStoreRequest.model_json_schema(),
        )
    ]
    

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handles incoming tool calls."""
    logger.info(f"Received call_tool request for '{name}'")
    
    # Get components from context
    qdrant_connector: QdrantConnector = server.request_context.lifespan_context.get("qdrant_connector")
    
    # --- Tool Business Logic --- #
    match name:
        case ToolNames.QDRANT_STORE.value:
            try:        

                # Validate input
                request = QdrantStoreRequest(**arguments)
                
                # Store the information
                entry = Entry(content=request.information, metadata=request.metadata)
                
                await qdrant_connector.store(entry, collection_name=request.collection_name)
                
                # Return success message
                msg = f"Remembered: {request.information} in collection {request.collection_name}"
                
                logger.info(f"Successfully stored information in Qdrant")
                return [TextContent(type="text", text=msg)]
                
            except ValidationError as ve:
                error_msg = f"Invalid arguments for tool '{name}': {ve}"
                logger.warning(error_msg)
                return [TextContent(type="text", text=error_msg)]
                
            except Exception as e:
                error_msg = f"An error occurred while storing information: {str(e)}"
                logger.error(f"Error storing information: {e}", exc_info=True)
                return [TextContent(type="text", text=error_msg)]
                
        case ToolNames.QDRANT_FIND.value:
            try:

                # Validate input
                request = QdrantFindRequest(**arguments)
                
                # Search for entries
                entries = await qdrant_connector.search(
                    request.query,
                    collection_name=request.collection_name,
                    limit=request.search_limit
                )
                
                # Format response
                if not entries:
                    return [TextContent(type="text", text=f"No information found for the query '{request.query}'")]
    
                content = [f"Results for the query '{request.query}'"]
                for entry in entries:
                    content.append(str(entry))
                
                logger.info(f"Successfully searched Qdrant")
                return [TextContent(type="text", text="\n".join(content))]
                
            except ValidationError as ve:
                error_msg = f"Invalid arguments for tool '{name}': {ve}"
                logger.warning(error_msg)
                return [TextContent(type="text", text=error_msg)]
                
            except Exception as e:
                error_msg = f"An error occurred while searching: {str(e)}"
                logger.error(f"Error searching Qdrant: {e}", exc_info=True)
                return [TextContent(type="text", text=error_msg)]
                
        case _:
            logger.warning(f"Received call for unknown tool: {name}")
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
