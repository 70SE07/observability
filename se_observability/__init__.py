"""Observability — логування, request correlation, метрики.

Інфраструктурний модуль за CONVENTIONS.md.
ЦКП: повна спостережуваність системи (логи, контекст запиту, timing/cost).

Public API:
- get_logger(name) → Logger
- request_id_var: ContextVar для кореляції запитів
- RequestIdMiddleware: Starlette middleware (request_id_var + X-Request-Id header)
"""

from .context import RequestIdMiddleware, request_id_var
from .logger import get_logger

__all__ = ["RequestIdMiddleware", "get_logger", "request_id_var"]
