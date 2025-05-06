import argparse
import os
import logging
import sys
from dotenv import load_dotenv

from starlette.routing import Route, Mount
from mcp.server.sse import SseServerTransport
from mcp.server import Server
from starlette.requests import Request
import uvicorn
from starlette.applications import Starlette
from starlette.responses import Response


load_dotenv()

# Configure logging
from mcp_server_arxiv.logging_config import configure_logging
configure_logging()
logger = logging.getLogger(__name__)


def create_starlette_app(mcp_server: Server, *, debug: bool = False) -> Starlette:
    sse = SseServerTransport("/messages/")
    async def handle_sse(request: Request) -> Response:
        async with sse.connect_sse(
            request.scope,
            request.receive,
            request._send,  
        ) as (read_stream, write_stream):
            init_options = mcp_server.create_initialization_options()
            await mcp_server.run(read_stream, write_stream, init_options)
        return Response()
    return Starlette(
        debug=debug,
        routes=[Route("/sse", endpoint=handle_sse), Mount("/messages/", app=sse.handle_post_message)],
        lifespan=mcp_server.lifespan
    )

if __name__ == "__main__":
    try:
        from mcp_server_arxiv.server import server as arxiv_mcp_server
    except Exception as import_err:
         logger.critical(f"Failed import/init ArXiv MCP server: {import_err}", exc_info=True)
         sys.exit(1)

    # --- Command Line Argument Parsing ---
    parser = argparse.ArgumentParser(description='Run MCP Starlette server for ArXiv Search')
    parser.add_argument(
        '--host',
        default=os.getenv("MCP_ARXIV_HOST", "localhost"),
        help='Host (Default: MCP_ARXIV_HOST or localhost)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=int(os.getenv("MCP_ARXIV_PORT", "8006")), # Use 8006 as default
        help='Port (Default: MCP_ARXIV_PORT or 8006)'
    )
    args = parser.parse_args()

    # --- Server Configuration ---
    reload_enabled = os.getenv("MCP_ARXIV_RELOAD", "false").lower() == "true"
    log_level_str = os.getenv("MCP_ARXIV_LOG_LEVEL", "info").lower()

    # --- Create and Run Application ---
    starlette_app = create_starlette_app(arxiv_mcp_server, debug=reload_enabled)

    logger.info(f"Starting MCP ArXiv Server on http://{args.host}:{args.port}")
    logger.info(f"Log level set to: {log_level_str.upper()}")
    if reload_enabled:
        logger.warning("Reload mode is enabled. DO NOT use in production.")

    # Run Uvicorn server
    try:
        uvicorn.run(
            "mcp_server_arxiv.__main__:starlette_app" if reload_enabled else starlette_app,
            factory=reload_enabled,
            host=args.host,
            port=args.port,
            reload=reload_enabled,
            log_level=log_level_str,
        )
    except Exception as uvicorn_err:
         logger.critical(f"Failed to start Uvicorn server: {uvicorn_err}", exc_info=True)
         sys.exit(1)