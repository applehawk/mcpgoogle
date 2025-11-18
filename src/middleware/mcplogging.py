import uuid
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import json
from typing import Callable

logger = logging.getLogger("mcp.request")

SENSITIVE_HEADERS = {"authorization", "x-api-key", "cookie"}
SENSITIVE_JSON_KEYS = {"access_token", "refresh_token", "password", "token", "api_key"}

def redact_headers(headers: dict):
    return {k: ("***" if k.lower() in SENSITIVE_HEADERS else v) for k, v in headers.items()}

def redact_json(obj):
    # рекурсивно маскирует ключи доступа в json-е
    if isinstance(obj, dict):
        return {k: ("***" if k in SENSITIVE_JSON_KEYS else redact_json(v)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [redact_json(x) for x in obj]
    return obj

class MCPLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable):
        # генерируем correlation id (или возьмём из заголовка если есть)
        request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
        extra = {"request_id": request_id}

        # читаем тело (будьте осторожны с большими телами)
        raw_body = await request.body()
        try:
            parsed_body = json.loads(raw_body.decode("utf-8")) if raw_body else None
            parsed_body_redacted = redact_json(parsed_body) if parsed_body else None
        except Exception:
            parsed_body = None
            parsed_body_redacted = "<non-json / parse error>"

        # лог входящего (ограничиваем длину тела)
        logger.info("INCOMING %s %s headers=%s body=%s",
                    request.method,
                    request.url.path,
                    redact_headers(dict(request.headers)),
                    json.dumps(parsed_body_redacted)[:10000],
                    extra=extra)

        # forward request
        response: Response = await call_next(request)

        # лог ответа (тоже ограничивать размер)
        resp_body = None
        try:
            # response.body может быть stream, поэтому безопасно читать .body() у Starlette Response
            resp_body_bytes = await response.body()
            resp_body_text = resp_body_bytes.decode("utf-8", errors="replace")
            try:
                resp_body = json.loads(resp_body_text)
                resp_body_redacted = redact_json(resp_body)
            except Exception:
                resp_body_redacted = resp_body_text[:10000]
        except Exception:
            resp_body_redacted = "<could not read response body>"

        logger.info("OUTGOING %s %s status=%s body=%s",
                    request.method,
                    request.url.path,
                    response.status_code,
                    json.dumps(resp_body_redacted)[:10000],
                    extra=extra)

        # вернуть оригинальный response (в Starlette читаемый body уже использован, но call_next вернёт корректно)
        return response
