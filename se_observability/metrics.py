"""Metrics — структуроване відстеження timing та cost.

ЦКП: структуровані метрики з prefix "metric" для парсингу лог-агрегаторами.
Не обчислює pricing (це infra/gemini). Тільки записує та емітить.
"""

import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field

from .logger import get_logger

log = get_logger("metrics")


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
        elapsed = self.elapsed_s
        extra_str = " ".join(f"{k}={v}" for k, v in self.extra.items())
        log.info(
            "metric  endpoint=%s elapsed=%.2fs cost=$%.4f model=%s %s",
            self.endpoint,
            elapsed,
            self.cost_usd,
            self.model or "-",
            extra_str,
        )


@contextmanager
def track(endpoint: str) -> Iterator[RequestMetrics]:
    """Context manager for timing an endpoint call. Emits on exit."""
    m = RequestMetrics(endpoint=endpoint)
    yield m
    m.emit()
