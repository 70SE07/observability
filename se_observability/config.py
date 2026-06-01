"""Logging Config — источник правды о настройках логирования (Триада: Config).

ЦКП: валидированные настройки логирования, готовые к использованию.
Знает ОТКУДА брать параметры (env / явные аргументы), не знает КАК собирать
логирование — это забота logger.py. По CONVENTIONS.md: «Config — источник
правды о настройках. Знает откуда брать параметры. Не знает зачем они нужны».
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# Сторонние SDK, чьи логи по умолчанию заворачиваем в файловый handler.
_DEFAULT_ROUTE_SDKS = ("google.genai", "httpx", "google.api_core.retry")


def parse_module_levels(raw: str) -> dict[str, str]:
    """Распарсить LOG_LEVELS="ns=LEVEL,ns2=LEVEL2" → dict."""
    result: dict[str, str] = {}
    for pair in raw.split(","):
        pair = pair.strip()
        if "=" in pair:
            ns, level = pair.split("=", 1)
            result[ns.strip()] = level.strip().upper()
    return result


@dataclass(frozen=True)
class LoggingConfig:
    """Валидированные настройки логирования. Источник — env или явные аргументы."""

    service_name: str
    log_dir: Path
    log_level: str
    log_format: str
    module_levels: dict[str, str]
    route_sdks: tuple[str, ...]
    max_bytes: int
    backup_count: int

    @staticmethod
    def from_env(
        service_name: str | None = None,
        *,
        log_dir: str | Path | None = None,
        log_level: str | None = None,
        log_format: str | None = None,
        module_log_levels: dict[str, str] | None = None,
        route_sdks: tuple[str, ...] = _DEFAULT_ROUTE_SDKS,
        max_bytes: int = 10_000_000,
        backup_count: int = 5,
    ) -> "LoggingConfig":
        """Собрать настройки: явный аргумент имеет приоритет над env, env — над дефолтом.

        service_name: аргумент → env SE_OBSERVABILITY_SERVICE → "app".
        """
        svc = (
            service_name
            or os.environ.get("SE_OBSERVABILITY_SERVICE", "")
            or "app"
        ).strip() or "app"
        levels = (
            module_log_levels
            if module_log_levels is not None
            else parse_module_levels(os.environ.get("LOG_LEVELS", ""))
        )
        return LoggingConfig(
            service_name=svc,
            log_dir=Path(log_dir or os.environ.get("LOG_DIR", "logs")),
            log_level=(log_level or os.environ.get("LOG_LEVEL", "INFO")).upper(),
            log_format=log_format or os.environ.get("LOG_FORMAT", "text"),
            module_levels=dict(levels),
            route_sdks=route_sdks,
            max_bytes=max_bytes,
            backup_count=backup_count,
        )
