from mcp.server.fastmcp import FastMCP
from fastmcp.server.auth.providers.debug import DebugTokenVerifier
from src import config

# Configure authentication if MCP_AUTH_TOKEN is set
auth = None
if config.MCP_AUTH_TOKEN:
    # Use DebugTokenVerifier for simple token-based auth
    # In production, consider using JWTVerifier or IntrospectionTokenVerifier
    auth = DebugTokenVerifier(
        validate=lambda token: token == config.MCP_AUTH_TOKEN,
        client_id="openai-agents",
        scopes=["read", "write", "execute"]
    )

# Initialize FastMCP with HTTP transport and authentication
mcp = FastMCP(
    name="MCPGoogle",
    auth=auth
)