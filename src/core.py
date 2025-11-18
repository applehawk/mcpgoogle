import logging
from logging.handlers import RotatingFileHandler
import sys
import json
from pythonjsonlogger.json import JsonFormatter  

from mcp.server.fastmcp import FastMCP
# from fastmcp.server.auth.providers.debug import DebugTokenVerifier
from src import config

# Configure authentication if MCP_AUTH_TOKEN is set
# auth = None
# if config.MCP_AUTH_TOKEN:
#     # Use DebugTokenVerifier for simple token-based auth
#     # In production, consider using JWTVerifier or IntrospectionTokenVerifier
#     auth = DebugTokenVerifier(
#         validate=lambda token: token == config.MCP_AUTH_TOKEN,
#         client_id="openai-agents",
#         scopes=["read", "write", "execute"]
#     )

# Initialize FastMCP with HTTP transport and authentication
mcp = FastMCP(
    name="MCPGoogle"
)

def setup_logging():
    root = logging.getLogger()
    # если нужно, можно выбрать другой default level
    root.setLevel(logging.INFO)

    # Если уже есть обработчики — не добавляем дубли (защита от повторных вызовов)
    handler_names = {type(h).__name__ + (getattr(h, 'stream', '') and str(h.stream)) for h in root.handlers}
    
    # Stream handler (stdout) — хорош для контейнеров / docker / kubernetes
    if "StreamHandler" not in handler_names:
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_fmt = '%(asctime)s %(levelname)s %(name)s %(message)s %(request_id)s'
        stream_handler.setFormatter(JsonFormatter(stream_fmt))
        stream_handler.addFilter(RequestIDFilter())
        root.addHandler(stream_handler)

    # Optional: rotating file for local debugging
    # создаём с проверкой — чтобы не дублировать
    if not any(isinstance(h, RotatingFileHandler) and getattr(h, "baseFilename", "") .endswith("mcp.log")
               for h in root.handlers):
        file_handler = RotatingFileHandler('mcp.log', maxBytes=10*1024*1024, backupCount=5)
        file_fmt = '%(asctime)s %(levelname)s %(name)s %(message)s %(request_id)s'
        file_handler.setFormatter(JsonFormatter(file_fmt))
        file_handler.addFilter(RequestIDFilter())
        root.addHandler(file_handler)

    # make sure noisy libs don't overwhelm logs (tune as needed)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
