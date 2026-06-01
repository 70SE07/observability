"""Metrics — структуроване відстеження timing та cost.

ЦКП: структурована метрика (timing + cost) у відкритому форматі — окремими
полями (extra "fields") для лог-агрегаторів, плюс читабельний msg для людини.
Не обчислює pricing (це infra/gemini). Тільки записує та емітить.
"""

import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field

from .contracts import LOG_FIELDS_KEY
from .logger import get_logger


@dataclass
class RequestMetrics:
    """Accumulated metrics for a single request lifecycle."""

    endpoint: str
    t0: float = field(default_factory=time.time)
    cost_usd: float = 0.0
    model: str = ""
    extra: dict[str, str | int | float] = field(default_factory=dict)

    @property
    def elapsed_s(self) -> float:
        return time.time() - self.t0

    def record_cost(self, cost: float, model: str = "") -> None:
        self.cost_usd += cost
        if model:
            self.model = model

    def emit(self) -> None:
        # Lazy logger acquisition — без side-effect на импорте модуля (как audit).
        log = get_logger("metrics")
        fields: dict[str, object] = {
            "endpoint": self.endpoint,
            "elapsed_s": round(self.elapsed_s, 2),
            "cost_usd": round(self.cost_usd, 4),
            "model": self.model or "-",
            **self.extra,
        }
        # Читабельный msg (text-формат) + structured fields отдельными ключами (JSON).
        readable = " ".join(f"{k}={v}" for k, v in fields.items())
        log.info("metric  %s", readable, extra={LOG_FIELDS_KEY: fields})


@contextmanager
def track(endpoint: str) -> Iterator[RequestMetrics]:
    """Context manager for timing an endpoint call.

    Метрика эмитится в finally — в обоих исходах (успех и ошибка), чтобы
    наблюдаемость не терялась именно на упавших запросах.
    """
    m = RequestMetrics(endpoint=endpoint)
    try:
        yield m
    finally:
        m.emit()
