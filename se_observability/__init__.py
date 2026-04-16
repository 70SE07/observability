"""Observability — shared utilities for SE microservices.

Usage:
    from se_observability import configure, get_logger

    configure(service_name="bridge")  # at startup
    log = get_logger("web")

See README.md для details.
"""

from . import audit
from .context import RequestIdFilter, RequestIdMiddleware, request_id_var
from .logger import configure, get_logger

__all__ = [
    "RequestIdFilter",
    "RequestIdMiddleware",
    "audit",
    "configure",
    "get_logger",
    "request_id_var",
]
