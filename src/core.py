from mcp.server.fastmcp import FastMCP
from starlette.responses import JSONResponse

# Initialize FastMCP with SSE transport
mcp = FastMCP(
    name="MCPGoogle",
    transport="sse"  # Enable Server-Sent Events transport
)

@mcp.custom_route("/health", methods=["GET"])
async def health_check(request):
    return JSONResponse({"status": "healthy", "service": "mcp-server"})