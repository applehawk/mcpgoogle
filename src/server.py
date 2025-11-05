# mcp_hub/server.py
from src.core import mcp  # instancia compartida

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