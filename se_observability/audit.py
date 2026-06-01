"""Audit trail — generic structured business events.

ЦКП: структурированное бизнес-событие в открытом формате — отдельными полями
(extra "fields", без потери данных) для лог-агрегаторов, плюс читабельный msg.

Package-level только **generic** API. Domain-specific wrappers (напр.
record_generation для generation service) — в каждом сервисе локально,
чтобы shared package не раздувался доменом (SRP).

Usage:
    from se_observability import audit
    audit.record_event("ideate", user=123, cost=0.05, refs=1)
"""

from __future__ import annotations

from .contracts import LOG_FIELDS_KEY
from .logger import get_logger


def record_event(action: str, **kv: object) -> None:
    """Generic structured audit event.

    Эмитит и читабельную строку (text-формат), и structured-поля (JSON).
    Structured-поля несут ПОЛНЫЕ значения (без схлопывания коллекций) — событие
    восстановимо из лога. Observability не знает domain поля — заказчик решает.

    Format (text msg): `audit action=<action> k=v ...`
    Format (json):     `{... "fields": {"action": ..., <k>: <v-as-is>}}`
    """
    # Lazy logger acquisition — get_logger() требует configure() called first.
    log = get_logger("audit")
    fields: dict[str, object] = {"action": action, **kv}
    readable = " ".join(f"{k}={_readable_value(v)}" for k, v in fields.items())
    log.info("audit %s", readable, extra={LOG_FIELDS_KEY: fields})


def _readable_value(v: object) -> str:
    """Компактное представление ТОЛЬКО для человекочитаемого text-msg.

    Полные значения уходят в structured "fields" (JSON-сериализация в форматтере),
    поэтому здесь допустимо сжатие коллекций для глаза — данные при этом не
    теряются (они есть в fields).
    """
    if isinstance(v, list | tuple):
        return f"[{len(v)}]"
    if isinstance(v, dict):
        return "{" + ",".join(str(k) for k in v) + "}"
    return str(v)
