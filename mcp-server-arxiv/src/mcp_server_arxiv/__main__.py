import argparse
import os
import logging
import sys
from dotenv import load_dotenv

from starlette.routing import Route, Mount
from mcp.server.sse import SseServerTransport
from mcp.server import Server as MCPServer 
from starlette.requests import Request
from starlette.responses import Response 
import uvicorn
from starlette.applications import Starlette

load_dotenv()


from mcp_server_arxiv.logging_config import configure_logging, LOGGING_CONFIG
from mcp_server_arxiv.server import server as arxiv_mcp_server
configure_logging() 

logger = logging.getLogger(__name__) 






def create_starlette_app(mcp_server_instance: MCPServer, *, debug: bool = False) -> Starlette:
    """Creates a Starlette application to serve the provided MCP server with SSE."""
    sse_transport = SseServerTransport("/messages/") 

    async def handle_sse_connection(request: Request) -> Response:
        async with sse_transport.connect_sse(
            request.scope,
            request.receive,
            request._send, 
        ) as (read_stream, write_stream):
            initialization_options = mcp_server_instance.create_initialization_options()
            await mcp_server_instance.run(
                read_stream,
                write_stream,
                initialization_options,
            )
        return Response()

    return Starlette(
        debug=debug,
        routes=[
            Route("/sse", endpoint=handle_sse_connection), 
            Mount("/messages/", app=sse_transport.handle_post_message), 
        ],
        lifespan=mcp_server_instance.lifespan
    )

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run MCP Starlette server for ArXiv Search')
    parser.add_argument(
        '--host',
        default=os.getenv("MCP_ARXIV_HOST", "localhost"),
        help='Host to bind to (Default: MCP_ARXIV_HOST or localhost)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=int(os.getenv("MCP_ARXIV_PORT", "8006")), 
        help='Port to listen on (Default: MCP_ARXIV_PORT or 8006)'
    )
    args = parser.parse_args()


    reload_enabled = os.getenv("MCP_ARXIV_RELOAD", "false").lower() in ("true", "1", "t", "yes")
    uvicorn_log_level = LOGGING_CONFIG.get("root", {}).get("level", "info").lower()


    # --- Create and Run Application ---
    try:
        starlette_app = create_starlette_app(arxiv_mcp_server, debug=reload_enabled)
    except Exception as app_create_err:
        logger.critical(f"Failed to create Starlette application: {app_create_err}", exc_info=True)
        sys.exit(1)

    logger.info(f"Starting MCP ArXiv Server on http://{args.host}:{args.port}")
    logger.info(f"Uvicorn log level set to: {uvicorn_log_level}")
    if reload_enabled:
        logger.warning("Hot reload is enabled. This is for development use only.")


    try:
        uvicorn.run(
            "mcp_server_arxiv.__main__:starlette_app" if reload_enabled else starlette_app,
            factory=reload_enabled, 
            host=args.host,
            port=args.port,
            reload=reload_enabled,
            log_level=uvicorn_log_level,
        )
    except Exception as uvicorn_err:
         logger.critical(f"Failed to start Uvicorn server: {uvicorn_err}", exc_info=True)
         sys.exit(1)