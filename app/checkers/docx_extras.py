"""Дополнительные проверки нормоконтроля .docx: подписи и список литературы.

Эти проверки вынесены в отдельный модуль, потому что они работают с
последовательностями абзацев целиком (а не с каждым по отдельности, как
основной чекер). Логика — паттерны на регулярных выражениях.

Что проверяется:

    1. Подписи к таблицам:
        — должны идти ПЕРЕД таблицей
        — формат: «Таблица N — Название» (с длинным тире, не дефисом)
        — нумерация сквозная, без пропусков
    2. Подписи к рисункам:
        — должны идти ПОСЛЕ рисунка
        — формат: «Рисунок N — Название»
        — нумерация сквозная
    3. Список литературы (если есть):
        — после заголовка «Список литературы» / «Список использованных источников»
          ожидаем нумерованный список
        — каждый источник должен начинаться с цифры и точки («1.», «2.» и т. д.)
"""
from __future__ import annotations

import re
from typing import Any

from docx.document import Document as DocxDocument
from docx.text.paragraph import Paragraph

# Регулярки специально допускают как длинное тире (—), так и обычный дефис (-)
# и короткое тире (–), чтобы потом сообщить пользователю, что нужно именно «—».
TABLE_CAPTION_RE = re.compile(r"^Таблица\s+(\d+)\s*([—–-])\s*(.+)", re.IGNORECASE)
FIGURE_CAPTION_RE = re.compile(r"^Рисунок\s+(\d+)\s*([—–-])\s*(.+)", re.IGNORECASE)

# Заголовки раздела «Список литературы» — разные варианты, как пишут студенты.
BIBLIOGRAPHY_HEADERS = (
    "список литературы",
    "список использованных источников",
    "библиографический список",
)

# Источник в библиографии должен начинаться с «1.», «2.», ... либо «1)».
BIB_ENTRY_RE = re.compile(r"^\s*\d+\s*[.)]\s+\S")


def check_table_captions(document: DocxDocument) -> list[dict[str, Any]]:
    """Проверяет подписи к таблицам.

    Логика: проходим по элементам тела документа в порядке их появления
    (через xml-дерево), смотрим, что находится непосредственно перед каждой
    таблицей. Если это абзац — он должен соответствовать паттерну подписи.
    """
    issues: list[dict[str, Any]] = []
    body = document.element.body
    children = list(body.iterchildren())

    table_index = 0
    expected_number = 0

    for i, child in enumerate(children):
        if not child.tag.endswith("}tbl"):
            continue
        table_index += 1
        expected_number += 1

        # Ищем непустой абзац перед таблицей
        prev_paragraph_text = None
        for j in range(i - 1, -1, -1):
            prev = children[j]
            if prev.tag.endswith("}p"):
                text = "".join(prev.itertext()).strip()
                if text:
                    prev_paragraph_text = text
                    break
        if prev_paragraph_text is None:
            issues.append(
                {
                    "location": f"Таблица №{table_index} в документе",
                    "code": "TABLE_NO_CAPTION",
                    "message": "Перед таблицей отсутствует подпись",
                    "description": (
                        f"Перед таблицей должна быть подпись формата "
                        f"«Таблица {expected_number} — Название»"
                    ),
                    "severity": "high",
                    "expected": f"Таблица {expected_number} — Название",
                    "actual": "подпись отсутствует",
                }
            )
            continue

        match = TABLE_CAPTION_RE.match(prev_paragraph_text)
        if not match:
            issues.append(
                {
                    "location": f"Таблица №{table_index}: подпись",
                    "code": "TABLE_CAPTION_FORMAT",
                    "message": (
                        "Подпись таблицы не соответствует формату «Таблица N — Название»"
                    ),
                    "description": (
                        "По ГОСТ 2.105 подпись таблицы оформляется как "
                        "«Таблица N — Название» (длинное тире, не дефис)"
                    ),
                    "severity": "medium",
                    "expected": f"Таблица {expected_number} — Название",
                    "actual": prev_paragraph_text[:80],
                }
            )
            continue

        actual_number = int(match.group(1))
        dash = match.group(2)
        if actual_number != expected_number:
            issues.append(
                {
                    "location": f"Таблица №{table_index}: подпись",
                    "code": "TABLE_NUMBER_MISMATCH",
                    "message": (
                        f"Номер таблицы в подписи ({actual_number}) "
                        f"не совпадает с порядком ({expected_number})"
                    ),
                    "description": "Таблицы нумеруются сквозно по порядку появления",
                    "severity": "medium",
                    "expected": f"Таблица {expected_number}",
                    "actual": f"Таблица {actual_number}",
                }
            )
        if dash != "—":
            issues.append(
                {
                    "location": f"Таблица №{table_index}: подпись",
                    "code": "TABLE_DASH_WRONG",
                    "message": "В подписи используется не длинное тире «—»",
                    "description": (
                        "Между номером и названием ставится длинное тире «—» "
                        "(символ U+2014), а не дефис «-» или короткое тире «–»"
                    ),
                    "severity": "low",
                    "expected": "—",
                    "actual": dash,
                }
            )

    return issues


def check_figure_captions(document: DocxDocument) -> list[dict[str, Any]]:
    """Проверяет подписи к рисункам (искомый паттерн в тексте абзацев).

    К сожалению, python-docx не позволяет легко найти inline-изображения,
    привязанные к конкретному месту, поэтому идём от обратного: ищем абзацы,
    которые ВЫГЛЯДЯТ как подписи к рисункам, и проверяем их формат.
    """
    issues: list[dict[str, Any]] = []
    figure_caption_count = 0

    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if not text:
            continue
        # Ищем варианты «Рис.», «Рисунок», «Figure»
        if not re.match(r"^Рис(\.|унок)\s+\d+", text, re.IGNORECASE):
            continue
        figure_caption_count += 1
        match = FIGURE_CAPTION_RE.match(text)
        if not match:
            issues.append(
                {
                    "location": f"Рисунок №{figure_caption_count}: подпись",
                    "code": "FIGURE_CAPTION_FORMAT",
                    "message": (
                        "Подпись рисунка не соответствует формату «Рисунок N — Название»"
                    ),
                    "description": (
                        "По ГОСТ подпись рисунка оформляется как "
                        "«Рисунок N — Название» (длинное тире, не дефис; "
                        "слово «Рисунок» полностью, не «Рис.»)"
                    ),
                    "severity": "medium",
                    "expected": "Рисунок N — Название",
                    "actual": text[:80],
                }
            )
            continue
        expected_number = figure_caption_count
        actual_number = int(match.group(1))
        dash = match.group(2)
        if actual_number != expected_number:
            issues.append(
                {
                    "location": f"Рисунок №{figure_caption_count}: подпись",
                    "code": "FIGURE_NUMBER_MISMATCH",
                    "message": (
                        f"Номер рисунка в подписи ({actual_number}) "
                        f"не совпадает с порядком ({expected_number})"
                    ),
                    "description": "Рисунки нумеруются сквозно по порядку появления",
                    "severity": "medium",
                    "expected": f"Рисунок {expected_number}",
                    "actual": f"Рисунок {actual_number}",
                }
            )
        if dash != "—":
            issues.append(
                {
                    "location": f"Рисунок №{figure_caption_count}: подпись",
                    "code": "FIGURE_DASH_WRONG",
                    "message": "В подписи рисунка используется не длинное тире «—»",
                    "description": (
                        "Между номером и названием ставится длинное тире «—»"
                    ),
                    "severity": "low",
                    "expected": "—",
                    "actual": dash,
                }
            )

    return issues


def check_bibliography(document: DocxDocument) -> list[dict[str, Any]]:
    """Проверяет наличие и базовое оформление списка литературы.

    Алгоритм:
        1. Ищем абзац-заголовок «Список литературы» / «Список использованных
           источников» / «Библиографический список».
        2. Если не нашли — это уже замечание (для академической работы список
           литературы обязателен).
        3. Если нашли — собираем все непустые абзацы после него до конца
           документа и проверяем, что каждый начинается с «N.» или «N)».
    """
    issues: list[dict[str, Any]] = []
    paragraphs = document.paragraphs
    biblio_start = None

    for i, paragraph in enumerate(paragraphs):
        text = paragraph.text.strip().lower().rstrip(".:")
        if text in BIBLIOGRAPHY_HEADERS:
            biblio_start = i
            break

    if biblio_start is None:
        # Не штрафуем, но информируем — у студента может быть и не положено
        # (например, рабочая записка). Уровень — low.
        issues.append(
            {
                "location": "Документ в целом",
                "code": "BIBLIOGRAPHY_MISSING",
                "message": "Не найден раздел «Список литературы»",
                "description": (
                    "В академической работе ожидается раздел «Список литературы» "
                    "или «Список использованных источников»"
                ),
                "severity": "low",
                "expected": "наличие раздела",
                "actual": "не найден",
            }
        )
        return issues

    # Проверяем, что после заголовка идут пронумерованные источники
    entries_found = 0
    incorrectly_formatted: list[tuple[int, str]] = []

    for paragraph in paragraphs[biblio_start + 1:]:
        text = paragraph.text.strip()
        if not text:
            continue
        # Если попался ещё один заголовок раздела — выходим
        if (
            text.lower().rstrip(".:") in BIBLIOGRAPHY_HEADERS
            or "приложение" in text.lower()[:15]
        ):
            break
        if BIB_ENTRY_RE.match(text):
            entries_found += 1
        else:
            # Это либо абзац-комментарий, либо просто кривая запись
            incorrectly_formatted.append((entries_found + 1, text[:80]))

    if entries_found == 0:
        issues.append(
            {
                "location": "Раздел «Список литературы»",
                "code": "BIBLIOGRAPHY_EMPTY",
                "message": "Раздел найден, но в нём нет пронумерованных источников",
                "description": (
                    "Каждый источник в списке литературы оформляется отдельным "
                    "пунктом и начинается с номера: «1. Иванов И. И. ...»"
                ),
                "severity": "high",
                "expected": "нумерованный список источников",
                "actual": "источники не найдены",
            }
        )
    elif incorrectly_formatted:
        # Сообщаем максимум о трёх таких — иначе отчёт раздуется
        for next_number, snippet in incorrectly_formatted[:3]:
            issues.append(
                {
                    "location": f"Список литературы, после источника №{next_number - 1}",
                    "code": "BIBLIOGRAPHY_ENTRY_FORMAT",
                    "message": "Запись не начинается с номера и точки",
                    "description": (
                        "Каждый источник оформляется как «N. Автор. Название…»"
                    ),
                    "severity": "medium",
                    "expected": "N. ...",
                    "actual": snippet,
                }
            )

    return issues
