"""Logger — сборка подсистемы логирования из готового LoggingConfig.

ЦКП: get_logger(name) → configured Logger в namespace {service}.{name}.

Принимает готовые настройки (config.py — Триада Config); НЕ знает, откуда они
берутся (env — забота config.py). PII-маскирование — отдельная единица
(redaction.py). Import package — без side effects, весь setup внутри configure().

API (контракт, сохранён обратно-совместимым):
    configure(service_name=None, *, config=None, ...) — один раз at startup
    get_logger(name) → Logger
Fail-fast: get_logger() до configure() → RuntimeError.
"""

from __future__ import annotations

import json
import logging
import sys
from logging.handlers import RotatingFileHandler

from .config import LoggingConfig
from .context import NO_REQUEST_ID, RequestIdFilter
from .redaction import PIIFilter

# ── Module state (set by configure) ──
_SERVICE_NAME: str | None = None
_MODULE_LOG_LEVELS: dict[str, str] = {}


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
            "rid": getattr(record, "request_id", NO_REQUEST_ID),
            "msg": record.getMessage(),
            "service": self._service,
        }
        # Structured-поля от metrics/audit (через log.info(..., extra={"fields": {...}}))
        # эмитятся ОТДЕЛЬНЫМИ ключами JSON, а не подстрокой внутри msg —
        # открытый формат, пригодный для независимых лог-агрегаторов (Unix §3).
        fields = getattr(record, "fields", None)
        if fields is not None:
            data["fields"] = fields
        return json.dumps(data, ensure_ascii=False, default=str)


# ── Один источник правды «как собрать наш handler» (DRY) ──


def _build_handler(
    handler: logging.Handler,
    formatter: logging.Formatter,
    level: int,
    filters: list[logging.Filter],
) -> logging.Handler:
    handler.setFormatter(formatter)
    handler.setLevel(level)
    for f in filters:
        handler.addFilter(f)
    return handler


def configure(
    service_name: str | None = None,
    *,
    config: LoggingConfig | None = None,
    log_dir: str | None = None,
    log_level: str | None = None,
    log_format: str | None = None,
    log_max_bytes: int = 10_000_000,
    log_backup_count: int = 5,
    module_log_levels: dict[str, str] | None = None,
    route_sdks: tuple[str, ...] = ("google.genai", "httpx", "google.api_core.retry"),
) -> None:
    """Initialize observability для service. Call once at startup.

    Принимает либо готовый LoggingConfig (`config=`), либо собирает его из
    `service_name` + env/аргументов (обратно совместимо с прежней сигнатурой
    `configure(service_name=...)`). Источник настроек целиком в config.py.

    Idempotent: повторный вызов — no-op (warning при другом service_name).
    """
    global _SERVICE_NAME, _MODULE_LOG_LEVELS

    if _SERVICE_NAME is not None:
        incoming = (config.service_name if config else service_name) or _SERVICE_NAME
        if incoming != _SERVICE_NAME:
            logging.getLogger(_SERVICE_NAME).warning(
                "se_observability.configure() called again с другим service_name: %r → %r — ignored",
                _SERVICE_NAME,
                incoming,
            )
        return

    cfg = config or LoggingConfig.from_env(
        service_name,
        log_dir=log_dir,
        log_level=log_level,
        log_format=log_format,
        module_log_levels=module_log_levels,
        route_sdks=route_sdks,
        max_bytes=log_max_bytes,
        backup_count=log_backup_count,
    )

    _SERVICE_NAME = cfg.service_name
    _MODULE_LOG_LEVELS = cfg.module_levels

    try:
        cfg.log_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise RuntimeError(
            f"se_observability.configure: cannot create log directory {cfg.log_dir}: {e}"
        ) from e

    if cfg.log_format == "json":
        formatter: logging.Formatter = JSONFormatter(cfg.service_name)
    else:
        formatter = SingleLineFormatter(
            "%(asctime)s.%(msecs)03d | %(levelname)-7s | %(name)s | [%(request_id)s] | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    filters: list[logging.Filter] = [RequestIdFilter(), PIIFilter()]

    console = _build_handler(
        logging.StreamHandler(sys.stdout),
        formatter,
        getattr(logging, cfg.log_level, logging.INFO),
        filters,
    )
    file_handler = _build_handler(
        RotatingFileHandler(
            cfg.log_dir / "app.log",
            maxBytes=cfg.max_bytes,
            backupCount=cfg.backup_count,
            encoding="utf-8",
        ),
        formatter,
        logging.DEBUG,
        filters,
    )

    root = logging.getLogger(cfg.service_name)
    root.setLevel(logging.DEBUG)
    root.addHandler(console)
    root.addHandler(file_handler)

    for sdk_name in cfg.route_sdks:
        sdk = logging.getLogger(sdk_name)
        sdk.setLevel(logging.DEBUG)
        sdk.addHandler(file_handler)


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
