"""Request context — кореляція запитів frontend ↔ backend.

Три компоненти:
- request_id_var: ContextVar, встановлюється на кожен HTTP запит
- RequestIdFilter: додає request_id до кожного лог-запису
- RequestIdMiddleware: Starlette middleware, генерує rid + X-Request-Id header
"""

import contextvars
import logging
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

# ── ContextVar: доступний з будь-якого місця в async контексті ──

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")


# ── Filter: інжектує request_id в кожен лог-запис ──


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get("-")  # type: ignore[attr-defined]
        return True


# ── Middleware: генерує request_id + повертає X-Request-Id header ──


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        rid = uuid.uuid4().hex[:8]
        token = request_id_var.set(rid)
        try:
            response = await call_next(request)
            response.headers["X-Request-Id"] = rid
            return response
        finally:
            request_id_var.reset(token)
