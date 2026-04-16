"""Logger — service-agnostic logging infrastructure.

ЦКП: get_logger(name) → configured Logger with request_id, file + console output.

Service namespace prefix via SE_OBSERVABILITY_SERVICE env (default "app").
Each consuming service sets this env so logs have clear service prefix:
  SE_OBSERVABILITY_SERVICE=bridge → logs namespace "bridge.{name}"
  SE_OBSERVABILITY_SERVICE=generation → "generation.{name}"
"""

import json
import logging
import os
import re
import sys
from logging.handlers import RotatingFileHandler

from .config import (
    LOG_BACKUP_COUNT,
    LOG_DIR,
    LOG_FORMAT,
    LOG_LEVEL,
    LOG_MAX_BYTES,
    MODULE_LOG_LEVELS,
)
from .context import RequestIdFilter

SERVICE_NAME: str = os.environ.get("SE_OBSERVABILITY_SERVICE", "app").strip() or "app"

# ── PII Filter ──
_PHONE_RE = re.compile(r"(?<!\d)(\+?\d{1,3}[-.\s]?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{2,4})(?!\d)")


class PIIFilter(logging.Filter):
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
    def format(self, record: logging.LogRecord) -> str:
        data = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S") + f".{int(record.msecs):03d}Z",
            "level": record.levelname,
            "logger": record.name,
            "rid": getattr(record, "request_id", "-"),
            "msg": record.getMessage(),
            "service": SERVICE_NAME,
        }
        return json.dumps(data, ensure_ascii=False)


# ── Setup handlers ──
try:
    LOG_DIR.mkdir(exist_ok=True)
except OSError as e:
    raise RuntimeError(f"Observability: cannot create log directory {LOG_DIR}: {e}") from e

LOG_FILE = LOG_DIR / "app.log"

TEXT_FMT = "%(asctime)s.%(msecs)03d | %(levelname)-7s | %(name)s | [%(request_id)s] | %(message)s"
DATE_FMT = "%Y-%m-%d %H:%M:%S"

formatter: logging.Formatter = (
    JSONFormatter() if LOG_FORMAT == "json" else SingleLineFormatter(TEXT_FMT, datefmt=DATE_FMT)
)

rid_filter = RequestIdFilter()
pii_filter = PIIFilter()

console = logging.StreamHandler(sys.stdout)
console.setFormatter(formatter)
console.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
console.addFilter(rid_filter)
console.addFilter(pii_filter)

file_handler = RotatingFileHandler(
    LOG_FILE, maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUP_COUNT, encoding="utf-8"
)
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.DEBUG)
file_handler.addFilter(rid_filter)
file_handler.addFilter(pii_filter)

root = logging.getLogger(SERVICE_NAME)
root.setLevel(logging.DEBUG)
root.addHandler(console)
root.addHandler(file_handler)

# Route 3rd-party SDK logs through file_handler for retry/HTTP visibility
for sdk_name in ("google.genai", "httpx", "google.api_core.retry"):
    _sdk = logging.getLogger(sdk_name)
    _sdk.setLevel(logging.DEBUG)
    _sdk.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """Return a namespaced logger: '{SERVICE_NAME}.{name}'.

    LOG_LEVELS env supports per-module override:
      LOG_LEVELS="bridge.infra.db=DEBUG,bridge.web=WARNING"
    """
    full_name = f"{SERVICE_NAME}.{name}" if not name.startswith(SERVICE_NAME + ".") else name
    logger = logging.getLogger(full_name)
    if full_name in MODULE_LOG_LEVELS:
        logger.setLevel(getattr(logging, MODULE_LOG_LEVELS[full_name], logging.INFO))
    return logger
