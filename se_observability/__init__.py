"""Observability — набор самостоятельных инфраструктурных единиц для SE микросервисов.

Это НЕ единый модуль-цепочка, а агрегатор (фасад) самостоятельных cross-cutting
единиц, каждая со своей ЦКП и контрактом:
- config    — источник правды о настройках логирования (Триада: Config)
- logger    — сборка namespaced-логирования из настроек
- redaction — маскирование PII в лог-записях
- context   — request_id корреляция (наскрозная трассировка)
- metrics   — timing/cost метрики
- audit     — бизнес-события
Пакет лишь реэкспортирует их публичный API.

Usage:
    from se_observability import configure, get_logger

    configure(service_name="bridge")  # at startup (или env SE_OBSERVABILITY_SERVICE)
    log = get_logger("web")

See README.md для details.
"""

from . import audit, metrics
from .config import LoggingConfig
from .context import (
    NO_REQUEST_ID,
    REQUEST_ID_HEADER,
    RequestIdFilter,
    RequestIdMiddleware,
    request_id_var,
)
from .logger import configure, get_logger
from .redaction import PIIFilter

__all__ = [
    "NO_REQUEST_ID",
    "REQUEST_ID_HEADER",
    "LoggingConfig",
    "PIIFilter",
    "RequestIdFilter",
    "RequestIdMiddleware",
    "audit",
    "configure",
    "get_logger",
    "metrics",
    "request_id_var",
]
