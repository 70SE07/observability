"""Redaction — маскирование PII в лог-записях (заказчик: приватность данных).

ЦКП: лог-запись с замаскированными чувствительными данными. Знание о форматах
PII (телефоны и т.д.) живёт здесь, а не в logger — у logger другой заказчик
(сборка логирования) и другая причина изменения. logger подключает этот фильтр.
"""

from __future__ import annotations

import logging
import re

# Форматы маскируемых сущностей. Новый тип PII (e-mail/токен) добавляется ЗДЕСЬ,
# не затрагивая сборку логирования.
_PHONE_RE = re.compile(r"(?<!\d)(\+?\d{1,3}[-.\s]?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{2,4})(?!\d)")


class PIIFilter(logging.Filter):
    """Маскирует телефонные номера в лог-сообщениях как ***PHONE***."""

    def filter(self, record: logging.LogRecord) -> bool:
        if record.args:
            try:
                record.msg = record.msg % record.args
                record.args = None
            except (TypeError, ValueError):
                # Деградация форматирования не должна быть немой (стеклянный ящик):
                # помечаем запись видимым маркером, чтобы инженер увидел сбой,
                # и продолжаем маскирование уже-неформатированного msg.
                record.msg = f"{record.msg} [se-observability: PII-format-degraded]"
                record.args = None
        record.msg = _PHONE_RE.sub("***PHONE***", str(record.msg))
        return True
