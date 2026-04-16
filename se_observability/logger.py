"""Logger — service-namespaced logging infrastructure.

ЦКП: get_logger(name) → configured Logger с request_id + PII mask + file/console output.

API (контракт):
    configure(service_name, *, log_dir=None, log_level=None, log_format=None) — один раз at startup
    get_logger(name) → Logger в namespace {service_name}.{name}

Фиксированный fail-fast: get_logger() до configure() → RuntimeError.
Import package — без side effects. Все setup внутри configure().
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from .context import RequestIdFilter

# ── Module state (set by configure) ──
_SERVICE_NAME: str | None = None
_MODULE_LOG_LEVELS: dict[str, str] = {}


# ── PII Filter ──
_PHONE_RE = re.compile(r"(?<!\d)(\+?\d{1,3}[-.\s]?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{2,4})(?!\d)")


class PIIFilter(logging.Filter):
    """Маскирует телефонные номера в лог-сообщениях как ***PHONE***."""

    def filter(self, record: logging.LogRecord) -> bool:
        if record.args:
            try:
                record.msg = record.msg % record.args
                record.args = None
            except (TypeError, ValueError):
                pass
        record.msg = _PHONE_RE.sub("***PHONE***", str(record.msg))
        return True


# ── Formatters ──


class SingleLineFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return super().format(record).replace("\n", "\\n")


class JSONFormatter(logging.Formatter):
    def __init__(self, service_name: str) -> None:
        super().__init__()
        self._service = service_name

    def format(self, record: logging.LogRecord) -> str:
        data = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S") + f".{int(record.msecs):03d}Z",
            "level": record.levelname,
            "logger": record.name,
            "rid": getattr(record, "request_id", "-"),
            "msg": record.getMessage(),
            "service": self._service,
        }
        return json.dumps(data, ensure_ascii=False)


def configure(
    service_name: str,
    *,
    log_dir: str | Path | None = None,
    log_level: str | None = None,
    log_format: str | None = None,
    log_max_bytes: int = 10_000_000,
    log_backup_count: int = 5,
    module_log_levels: dict[str, str] | None = None,
    route_sdks: tuple[str, ...] = ("google.genai", "httpx", "google.api_core.retry"),
) -> None:
    """Initialize observability для service. Call once at startup.

    Args:
        service_name: logger namespace root, e.g. "bridge", "generation", "ideation"
        log_dir: directory для log files (default: env LOG_DIR or "./logs")
        log_level: root level (default: env LOG_LEVEL or "INFO")
        log_format: "text" | "json" (default: env LOG_FORMAT or "text")
        log_max_bytes: RotatingFileHandler max size
        log_backup_count: RotatingFileHandler backup count
        module_log_levels: per-module override (default: parse env LOG_LEVELS="k=V,...")
        route_sdks: list of 3rd-party logger names to route through file_handler

    Idempotent: if already configured, re-invocation no-op'ит (warning если разный service).
    """
    global _SERVICE_NAME, _MODULE_LOG_LEVELS

    if _SERVICE_NAME is not None:
        if _SERVICE_NAME != service_name:
            logging.getLogger(_SERVICE_NAME).warning(
                "se_observability.configure() called again с другим service_name: %r → %r — ignored",
                _SERVICE_NAME,
                service_name,
            )
        return

    _SERVICE_NAME = service_name.strip() or "app"

    log_dir_resolved = Path(log_dir or os.environ.get("LOG_DIR", "logs"))
    log_level_resolved = (log_level or os.environ.get("LOG_LEVEL", "INFO")).upper()
    log_format_resolved = log_format or os.environ.get("LOG_FORMAT", "text")

    if module_log_levels is None:
        _MODULE_LOG_LEVELS = _parse_module_levels(os.environ.get("LOG_LEVELS", ""))
    else:
        _MODULE_LOG_LEVELS = dict(module_log_levels)

    try:
        log_dir_resolved.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise RuntimeError(
            f"se_observability.configure: cannot create log directory {log_dir_resolved}: {e}"
        ) from e

    log_file = log_dir_resolved / "app.log"

    if log_format_resolved == "json":
        formatter: logging.Formatter = JSONFormatter(_SERVICE_NAME)
    else:
        text_fmt = (
            "%(asctime)s.%(msecs)03d | %(levelname)-7s | %(name)s "
            "| [%(request_id)s] | %(message)s"
        )
        formatter = SingleLineFormatter(text_fmt, datefmt="%Y-%m-%d %H:%M:%S")

    rid_filter = RequestIdFilter()
    pii_filter = PIIFilter()

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    console.setLevel(getattr(logging, log_level_resolved, logging.INFO))
    console.addFilter(rid_filter)
    console.addFilter(pii_filter)

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=log_max_bytes,
        backupCount=log_backup_count,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)
    file_handler.addFilter(rid_filter)
    file_handler.addFilter(pii_filter)

    root = logging.getLogger(_SERVICE_NAME)
    root.setLevel(logging.DEBUG)
    root.addHandler(console)
    root.addHandler(file_handler)

    for sdk_name in route_sdks:
        sdk = logging.getLogger(sdk_name)
        sdk.setLevel(logging.DEBUG)
        sdk.addHandler(file_handler)


def _parse_module_levels(raw: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for pair in raw.split(","):
        pair = pair.strip()
        if "=" in pair:
            ns, level = pair.split("=", 1)
            result[ns.strip()] = level.strip().upper()
    return result


def get_logger(name: str) -> logging.Logger:
    """Return a namespaced logger '{service_name}.{name}'.

    Raises:
        RuntimeError: if configure() was not called first.
    """
    if _SERVICE_NAME is None:
        raise RuntimeError(
            "se_observability not configured. Call "
            "`se_observability.configure(service_name='...')` before using get_logger()."
        )

    full_name = f"{_SERVICE_NAME}.{name}" if not name.startswith(_SERVICE_NAME + ".") else name
    logger = logging.getLogger(full_name)
    if full_name in _MODULE_LOG_LEVELS:
        logger.setLevel(getattr(logging, _MODULE_LOG_LEVELS[full_name], logging.INFO))
    return logger
