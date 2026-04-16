"""Audit trail — generic structured business events.

ЦКП: запись одной строки аудита в лог-файл с префиксом "audit action=...".

Package-level только **generic** API. Domain-specific wrappers (напр.
record_generation для generation service) — в каждом сервисе локально,
чтобы shared package не раздувался доменом (SRP).

Usage:
    from se_observability import audit
    audit.record_event("ideate", user=123, cost=0.05, refs=1)

    # В своём сервисе можно обернуть:
    # generation/audit.py:
    #   from se_observability.audit import record_event
    #   def record_generation(telegram_id, model, cost_usd, elapsed_s, **extra):
    #       record_event("generate", user=telegram_id, model=model,
    #                    cost_usd=cost_usd, elapsed_s=elapsed_s, **extra)
"""

from __future__ import annotations

from .logger import get_logger


def record_event(action: str, **kv: object) -> None:
    """Generic structured audit event.

    Observability не знает domain поля — каждый заказчик decides что ему важно.

    Format: `audit action=<action> k1=v1 k2=v2 ...`
    Lists рендерятся как `count=N`, dicts как `keys=a,b`. Всё остальное — str(v).
    """
    # Lazy logger acquisition — get_logger() требует configure() called first.
    # Audit callers ВСЕГДА происходят после startup, так что configure уже есть.
    log = get_logger("audit")
    parts = [f"action={action}"]
    for k, v in kv.items():
        parts.append(f"{k}={_format_value(v)}")
    log.info("audit " + " ".join(parts))


def _format_value(v: object) -> str:
    if isinstance(v, list | tuple):
        return f"count={len(v)}"
    if isinstance(v, dict):
        return ",".join(str(k) for k in v)
    return str(v)
