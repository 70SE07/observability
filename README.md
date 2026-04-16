# se-observability

Shared observability utilities для SE микросервисов (bridge, generation, ideation, etc).

## Что даёт

- `get_logger(name)` — namespaced logger с request_id + PII masking + rotating file handler
- `request_id_var` — ContextVar для cross-request correlation
- `RequestIdMiddleware` — Starlette middleware (inject X-Request-Id header)
- `audit.record_*` — audit log events
- `metrics.track()` — context manager для elapsed+cost tracking

## Использование

Каждый сервис ставит `SE_OBSERVABILITY_SERVICE=<service_name>` в env (bridge/.env, generation/.env, etc).
Logger namespace будет `{service}.{name}`.

```python
from se_observability import get_logger, RequestIdMiddleware, request_id_var

log = get_logger("web")
log.info("starting")
```

## Env

- `SE_OBSERVABILITY_SERVICE` — service namespace prefix (default "app")
- `LOG_LEVEL` — root logger level (default "INFO")
- `LOG_DIR` — log directory (default "logs")
- `LOG_FORMAT` — "text" or "json" (default "text")
- `LOG_LEVELS` — per-module override: `"service.module=LEVEL,..."`

## Установка

```toml
dependencies = [
    "se-observability @ git+https://github.com/70SE07/observability.git@v0.1.0",
]
```
