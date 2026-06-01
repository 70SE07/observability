"""Request context — наскрізна кореляція запитів frontend ↔ backend.

ЦКП: request_id, доступний з будь-якого місця async-контексту, проставлений
у кожен лог-запис і у HTTP-заголовок X-Request-Id. Забезпечує наскрізну
трасування через ланцюг сервісів (bridge → generation/ideation).

Компоненти:
- request_id_var: ContextVar — доступний з будь-якого місця async-контексту
- RequestIdFilter: інжектує request_id в кожен лог-запис
- RequestIdMiddleware: читає вхідний X-Request-Id (або генерує) на HTTP-границі
"""

import contextvars
import logging
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

# ── Контракт корреляции (DRY: единственный источник правды) ──
# Имя HTTP-заголовка, по которому сервисы в цепочке сшивают трассу.
REQUEST_ID_HEADER = "X-Request-Id"
# Sentinel-значение «request_id не установлен» (для лог-записей вне HTTP-контекста).
NO_REQUEST_ID = "-"


# ── ContextVar: доступний з будь-якого місця в async контексті ──

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default=NO_REQUEST_ID
)


# ── Filter: інжектує request_id в кожен лог-запис ──


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get(NO_REQUEST_ID)  # type: ignore[attr-defined]
        return True


# ── Middleware: читає/генерує request_id + повертає X-Request-Id header ──


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        # Наскрізна трасування: запит від вищестоящого сервісу (bridge →
        # generation/ideation) несе X-Request-Id — продовжуємо ту саму трасу.
        # Прямий вхід (без заголовка) — генеруємо новий id.
        rid = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex[:8]
        # request.state — для споживачів, що читають request.state.request_id
        # (bridge gateway forward прокидає його в upstream-запит).
        request.state.request_id = rid
        token = request_id_var.set(rid)
        try:
            response = await call_next(request)
            response.headers[REQUEST_ID_HEADER] = rid
            return response
        finally:
            request_id_var.reset(token)
