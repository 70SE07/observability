"""Контракт structured-полей лог-записи — единственный источник правды формы канала.

ЦКП: формальная точка опоры для structured-логирования — ключ и тип, через
которые producer'ы (metrics, audit, любой будущий emitter) кладут поля в
лог-запись, а consumer (JSONFormatter) их читает.

Это «замок и ключ» (Composability §3): совпала форма — единицы соединяются.
DRY §2 — единственное, для чего DRY действует между единицами, это контракт:
строка-ключ и форма живут ЗДЕСЬ и только здесь, не дублируются по producer'ам
и consumer'у.

Контракт фиксирует КАНАЛ (ключ + форма), а не ДОМЕН: какие именно поля внутри —
решает каждый producer (metrics: endpoint/cost; audit: action/...). Объединять
domain-наборы в одну схему нельзя — это разные знания разных заказчиков (DRY §3).
"""

from __future__ import annotations

from collections.abc import Mapping

# Ключ, под которым structured-поля кладутся в logging `extra=` и читаются из
# LogRecord. Единственный источник правды — литерал "fields" больше нигде.
LOG_FIELDS_KEY = "fields"

# Форма structured-полей: произвольные именованные значения, которые
# JSONFormatter сериализует отдельным ключом JSON (без потери данных).
LogFields = Mapping[str, object]
