"""Observability Config — налаштування логування.

Джерело правди про параметри логування.
Знає звідки брати параметри (env). Не знає навіщо вони потрібні.

LOG_LEVELS env — per-module override:
  LOG_LEVELS="bridge.infra.db=DEBUG,bridge.web=WARNING"
  Формат: comma-separated пари namespace=LEVEL
"""

import os
from pathlib import Path

LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO").upper()
LOG_DIR: Path = Path(
    os.environ.get("LOG_DIR", str(Path(__file__).resolve().parent.parent.parent / "logs"))
)
LOG_FORMAT: str = os.environ.get("LOG_FORMAT", "text")  # "text" or "json"
LOG_MAX_BYTES: int = 10_000_000
LOG_BACKUP_COUNT: int = 5


def parse_module_levels() -> dict[str, str]:
    """Парсити LOG_LEVELS env → dict namespace → level."""
    raw = os.environ.get("LOG_LEVELS", "")
    if not raw:
        return {}
    result: dict[str, str] = {}
    for pair in raw.split(","):
        pair = pair.strip()
        if "=" in pair:
            ns, level = pair.split("=", 1)
            result[ns.strip()] = level.strip().upper()
    return result


MODULE_LOG_LEVELS: dict[str, str] = parse_module_levels()
