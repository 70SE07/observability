"""Audit trail — бізнес-подiї для учёта.

ЦКП: структурований запис бізнес-подій (хто, що, скільки коштувало).
Зараз пише в лог-файл з prefix "audit". Коли з'явиться billing — перейде на DB.

Контракт:
- record_generation(telegram_id, model, cost, elapsed, **extra)
- record_edit(telegram_id, model, cost, elapsed, **extra)
- record_upscale(telegram_id, elapsed, **extra)

telegram_id — natural key з User контракту (не DB surrogate id).
"""

from dataclasses import dataclass

from .logger import get_logger

log = get_logger("audit")


@dataclass
class AuditEvent:
    """Одна бізнес-подія."""

    action: str
    telegram_id: int | None
    model: str
    cost_usd: float
    elapsed_s: float
    extra: dict[str, str | int | float]

    def emit(self) -> None:
        extra_str = " ".join(f"{k}={v}" for k, v in self.extra.items())
        log.info(
            "audit  action=%s user=%s model=%s cost=$%.4f elapsed=%.2fs %s",
            self.action,
            self.telegram_id or "anon",
            self.model or "-",
            self.cost_usd,
            self.elapsed_s,
            extra_str,
        )


def record_generation(
    telegram_id: int | None = None,
    model: str = "",
    cost_usd: float = 0.0,
    elapsed_s: float = 0.0,
    **extra: str | int | float,
) -> None:
    AuditEvent(
        action="generate",
        telegram_id=telegram_id,
        model=model,
        cost_usd=cost_usd,
        elapsed_s=elapsed_s,
        extra=extra,
    ).emit()


def record_edit(
    telegram_id: int | None = None,
    model: str = "",
    cost_usd: float = 0.0,
    elapsed_s: float = 0.0,
    **extra: str | int | float,
) -> None:
    AuditEvent(
        action="edit",
        telegram_id=telegram_id,
        model=model,
        cost_usd=cost_usd,
        elapsed_s=elapsed_s,
        extra=extra,
    ).emit()


def record_upscale(
    telegram_id: int | None = None,
    elapsed_s: float = 0.0,
    **extra: str | int | float,
) -> None:
    AuditEvent(
        action="upscale",
        telegram_id=telegram_id,
        model="-",
        cost_usd=0.0,
        elapsed_s=elapsed_s,
        extra=extra,
    ).emit()
