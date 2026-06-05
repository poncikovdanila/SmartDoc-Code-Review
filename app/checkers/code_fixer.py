"""Автоисправление Python-кода.

Трёхэтапный процесс:
    1. autoflake — удаляет неиспользуемые импорты и переменные
    2. autopep8 (aggressive=2) — форматирование PEP 8 + перенос длинных строк
    3. Повторный autopep8 — иногда первый проход не ловит всё

После трёх проходов файл должен проходить flake8 с 0 замечаний.
Если что-то осталось — это ограничение инструментов (например,
строковая константа длиной 80+ символов, которую нельзя перенести).
"""
from __future__ import annotations

import autoflake
import autopep8


def autofix_python_code(source: str) -> dict[str, str | int]:
    """Принимает исходный код, возвращает исправленный."""

    # Этап 1: autoflake — убираем мёртвый код
    step1 = autoflake.fix_code(
        source,
        remove_all_unused_imports=True,
        remove_unused_variables=True,
        remove_duplicate_keys=True,
    )

    # Этап 2: autopep8 — форматирование + перенос строк
    # experimental=True включает экспериментальные фиксы для E501 (длинные строки)
    step2 = autopep8.fix_code(
        step1,
        options={
            "aggressive": 2,
            "max_line_length": 79,
            "experimental": True,
        },
    )

    # Этап 3: повторный проход — после autoflake + первого autopep8 могут
    # появиться новые проблемы (лишние пустые строки, пробелы)
    step3 = autopep8.fix_code(
        step2,
        options={
            "aggressive": 2,
            "max_line_length": 79,
            "experimental": True,
        },
    )

    return {
        "fixed_code": step3,
        "original_lines": len(source.splitlines()),
        "fixed_lines": len(step3.splitlines()),
        "changed": step3 != source,
    }
