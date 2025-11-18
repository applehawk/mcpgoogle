# src/server.py
"""
MCP Google Hub Server

FastMCP server with Google services integration (Gmail, Calendar).
Fully compatible with OpenAI Agents hostedMcpTool.

Endpoints:
- /mcp/ - MCP protocol endpoint (JSON-RPC 2.0)
  - tools/list - List available tools
  - tools/call - Execute tool with arguments
- /health - Health check endpoint
"""
import logging
from src.core import mcp  # Shared FastMCP instance
from src.core import setup_logging
from src import config
from starlette.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware

# Import tools; their @mcp.tool() decorators register them automatically
from src.tools.gmail_tool import (
    gmail_get_message,
    gmail_list_unread,
    gmail_mark_as_read,
    gmail_modify_message,
    gmail_search_messages,
    gmail_send_message,
)

from src.tools.calendar_tool import calendar_upcoming


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request):
    """Health check endpoint for monitoring"""
    return JSONResponse({
        "status": "healthy",
        "service": "mcp-google-hub",
        # "auth_enabled": config.MCP_AUTH_TOKEN is not None,
        "transport": config.MCP_TRANSPORT
    })


# from src.middleware.mcplogging import MCPLoggingMiddleware
# # Configure CORS for OpenAI and other clients
# try:
#     if hasattr(mcp, 'app'):
#         origins = config.MCP_CORS_ORIGINS.split(",") if config.MCP_CORS_ORIGINS != "*" else ["*"]
#         mcp.app.add_middleware(
#             CORSMiddleware,
#             allow_origins=origins,
#             allow_credentials=True,
#             allow_methods=["GET", "POST", "OPTIONS"],
#             allow_headers=["*"],
#             expose_headers=["*"],
#         )
#         mcp.app.add_middleware(MCPLoggingMiddleware)
#         logging.getLogger("mcp.request").info("Attached MCPLoggingMiddleware to mcp.app")
#     else:
#         logging.getLogger("mcp.request").warning("mcp.app not exposed — cannot attach middleware programmatically")
# except Exception as e:
#     logging.getLogger("mcp.request").exception("Failed to attach middleware: %s", e)


if __name__ == "__main__":
    print(f"Starting MCP Google Hub server...")
    print(f"Transport: {config.MCP_TRANSPORT}")
    print(f"Host: {config.MCP_HOST}:{config.MCP_PORT}")
    print(f"MCP Endpoint: http://{config.MCP_HOST}:{config.MCP_PORT}/mcp/")
    # print(f"Auth: {'Enabled' if config.MCP_AUTH_TOKEN else 'Disabled (dev mode)'}")
    print(f"CORS Origins: {config.MCP_CORS_ORIGINS}")
    
    setup_logging()

    mcp.run(
        transport=config.MCP_TRANSPORT,
        port=config.MCP_PORT
    )