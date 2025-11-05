# mcp_hub/server.py
from mcp_hub.core import mcp  # instancia compartida

# Importa las tools; al importarse, sus @mcp.tool() ya quedan registradas
from mcp_hub.tools.gmail_tool import (
    gmail_get_message,
    gmail_list_unread,
    gmail_mark_as_read,
    gmail_modify_message,
    gmail_search_messages,
    gmail_send_message,
)
from mcp_hub.tools.calendar_tool import calendar_upcoming
from mcp_hub.tools.drive_tool import (
    drive_create_file,
    drive_delete_file,
    drive_download_file,
    drive_search,
    drive_share_file,
    drive_update_file,
)
from mcp_hub.tools.vscode_tool import vscode_open, vscode_open_file, vscode_install_ext
from mcp_hub.tools.github_tool import github_list_repos, github_create_issue
