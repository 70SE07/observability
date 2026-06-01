# se-observability

Набор самостоятельных observability-утилит для SE микросервисов (bridge, generation, ideation, render, factory).

Это **не модуль-цепочка**, а агрегатор cross-cutting единиц — каждая со своей ЦКП:

| Единица | ЦКП |
|---|---|
| `config` | валидированные настройки логирования (Триада: Config — источник правды о настройках) |
| `logger` | `get_logger(name)` → настроенный namespaced Logger |
| `redaction` | лог-запись с замаскированными PII |
| `context` | request_id, доступный из async-контекста + сквозная трассировка через `X-Request-Id` |
| `metrics` | структурированная timing/cost метрика |
| `audit` | структурированное бизнес-событие |

## Использование

```python
from se_observability import configure, get_logger, RequestIdMiddleware

configure(service_name="bridge")  # один раз at startup
log = get_logger("web")
log.info("starting")
```

`service_name` берётся из аргумента `configure(service_name=...)`, либо из env
`SE_OBSERVABILITY_SERVICE`, либо `"app"` (в этом порядке приоритета). Logger
namespace = `{service}.{name}`.

### Структурированные метрики и аудит

`metrics.track()` и `audit.record_event()` эмитят данные **двумя представлениями**:
читабельный `msg` (для `LOG_FORMAT=text`) и отдельные поля `fields` (для
`LOG_FORMAT=json` — открытый формат для лог-агрегаторов, без потери данных).

```python
from se_observability import metrics, audit

with metrics.track("/api/generate") as m:
    m.record_cost(0.046, model="gemini-3.1-flash-image-preview")
    m.extra["ratio"] = "1:1"
# → json: {"msg": "metric ...", "fields": {"endpoint": "/api/generate", "cost_usd": 0.046, ...}}

audit.record_event("generate", user=123, model="gemini-...", cost_usd=0.046)
```

## Env

- `SE_OBSERVABILITY_SERVICE` — service namespace (если не передан в `configure()`; default `"app"`)
- `LOG_LEVEL` — root logger level (default `"INFO"`)
- `LOG_DIR` — log directory (default `"logs"`)
- `LOG_FORMAT` — `"text"` или `"json"` (default `"text"`)
- `LOG_LEVELS` — per-module override: `"service.module=LEVEL,..."`

## Установка

Pin по immutable commit SHA (контракт потребителя — фиксированная версия):

```toml
dependencies = [
    "se-observability @ https://github.com/70SE07/observability/archive/<commit-sha>.tar.gz",
]
```
