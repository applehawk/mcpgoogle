# src/server.py
from src.core import mcp  # instancia compartida
from starlette.responses import JSONResponse

# Importa las tools; al importarse, sus @mcp.tool() ya quedan registradas
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
    return JSONResponse({"status": "healthy", "service": "mcp-server"})

if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)