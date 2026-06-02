"""Дополнительные проверки нормоконтроля .docx: подписи, библиография, форматирование.

Что проверяется:
    1. Подписи к таблицам
    2. Подписи к рисункам
    3. Список литературы
    4. Выравнивание текста (по ширине)
    5. Лишние пустые строки
    6. Оформление заголовков
    7. Нумерация страниц
    8. Гиперссылки
    9. Цвет текста
   10. Оформление таблиц (шрифт, границы)
   11. Лишние пробелы
   12. Наличие оглавления
"""
from __future__ import annotations

import re
from typing import Any

from docx.document import Document as DocxDocument
from docx.text.paragraph import Paragraph
from docx.shared import RGBColor, Pt
from docx.oxml.ns import qn
from docx.enum.text import WD_ALIGN_PARAGRAPH

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


# ═══════ 4. Выравнивание текста по ширине ═══════

def _is_heading(paragraph: Paragraph) -> bool:
    name = (paragraph.style.name or "").lower()
    return "heading" in name or "заголов" in name or "toc" in name


def check_text_alignment(document: DocxDocument) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    count = 0
    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if not text or len(text) < 20:
            continue
        if _is_heading(paragraph):
            continue
        if TABLE_CAPTION_RE.match(text) or re.match(r"^Рис", text, re.IGNORECASE):
            continue
        alignment = paragraph.alignment
        if alignment is not None and alignment != WD_ALIGN_PARAGRAPH.JUSTIFY:
            count += 1
            if count <= 5:
                preview = text[:50] + "…" if len(text) > 50 else text
                align_names = {
                    WD_ALIGN_PARAGRAPH.LEFT: "по левому краю",
                    WD_ALIGN_PARAGRAPH.CENTER: "по центру",
                    WD_ALIGN_PARAGRAPH.RIGHT: "по правому краю",
                }
                issues.append({
                    "location": f"Абзац: «{preview}»",
                    "code": "ALIGN_NOT_JUSTIFY",
                    "message": "Текст не выровнен по ширине",
                    "description": "Основной текст работы выравнивается по ширине (ГОСТ 7.32)",
                    "severity": "medium",
                    "expected": "по ширине (justify)",
                    "actual": align_names.get(alignment, str(alignment)),
                })
    if count > 5:
        issues.append({
            "location": "Документ в целом",
            "code": "ALIGN_NOT_JUSTIFY",
            "message": f"Ещё {count - 5} абзацев не выровнены по ширине",
            "description": "Основной текст выравнивается по ширине",
            "severity": "medium",
            "expected": "по ширине", "actual": f"{count} абзацев",
        })
    return issues


# ═══════ 5. Лишние пустые строки ═══════

def check_extra_blank_lines(document: DocxDocument) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    consecutive_empty = 0
    reported = 0
    for paragraph in document.paragraphs:
        if not paragraph.text.strip():
            consecutive_empty += 1
        else:
            if consecutive_empty >= 2 and reported < 5:
                preview = paragraph.text.strip()[:40]
                issues.append({
                    "location": f"Перед абзацем: «{preview}»",
                    "code": "EXTRA_BLANK_LINES",
                    "message": f"{consecutive_empty} пустых строк подряд",
                    "description": "Лишние пустые строки. Допускается не более одной.",
                    "severity": "low",
                    "expected": "не более 1", "actual": f"{consecutive_empty}",
                })
                reported += 1
            consecutive_empty = 0
    return issues


# ═══════ 6. Оформление заголовков ═══════

def check_headings(document: DocxDocument) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for paragraph in document.paragraphs:
        if not _is_heading(paragraph):
            continue
        text = paragraph.text.strip()
        if not text:
            continue
        if text.endswith("."):
            issues.append({
                "location": f"Заголовок: «{text[:60]}»",
                "code": "HEADING_ENDS_WITH_DOT",
                "message": "Заголовок заканчивается точкой",
                "description": "По ГОСТ заголовки не заканчиваются точкой",
                "severity": "medium",
                "expected": "без точки", "actual": text[-10:],
            })
        has_non_bold = any(run.text.strip() and not run.bold for run in paragraph.runs)
        if has_non_bold:
            issues.append({
                "location": f"Заголовок: «{text[:60]}»",
                "code": "HEADING_NOT_BOLD",
                "message": "Заголовок не выделен жирным",
                "description": "Заголовки оформляются полужирным начертанием",
                "severity": "medium",
                "expected": "полужирный", "actual": "обычный",
            })
    return issues


# ═══════ 7. Нумерация страниц ═══════

def check_page_numbers(document: DocxDocument) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    has_page_numbers = False
    for section in document.sections:
        for part in (section.footer, section.header):
            if part is None:
                continue
            xml = part._element.xml
            if "fldChar" in xml or "PAGE" in xml or "w:fldSimple" in xml:
                has_page_numbers = True
                break
        if has_page_numbers:
            break
    if not has_page_numbers:
        issues.append({
            "location": "Документ в целом",
            "code": "NO_PAGE_NUMBERS",
            "message": "Не найдена нумерация страниц",
            "description": "Страницы нумеруются арабскими цифрами (ГОСТ 7.32)",
            "severity": "medium",
            "expected": "нумерация страниц", "actual": "не найдена",
        })
    return issues


# ═══════ 8. Гиперссылки ═══════

def check_hyperlinks(document: DocxDocument) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    link_count = sum(1 for p in document.paragraphs if "w:hyperlink" in p._element.xml)
    if link_count > 0:
        issues.append({
            "location": "Документ в целом",
            "code": "HYPERLINKS_FOUND",
            "message": f"Найдено гиперссылок: {link_count}",
            "description": "Гиперссылки следует убрать или оформить обычным текстом",
            "severity": "low",
            "expected": "обычный текст", "actual": f"{link_count} гиперссылок",
        })
    return issues


# ═══════ 9. Цвет текста ═══════

def check_text_color(document: DocxDocument) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    colored = sum(
        1 for p in document.paragraphs for r in p.runs
        if r.text.strip() and r.font.color and r.font.color.rgb
        and r.font.color.rgb != RGBColor(0, 0, 0)
    )
    if colored > 0:
        issues.append({
            "location": "Документ в целом",
            "code": "COLORED_TEXT",
            "message": f"Найден цветной текст: {colored} фрагментов",
            "description": "Весь текст должен быть чёрного цвета",
            "severity": "medium",
            "expected": "чёрный", "actual": f"{colored} цветных фрагментов",
        })
    return issues


# ═══════ 10. Оформление таблиц ═══════

def check_table_formatting(document: DocxDocument) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for idx, table in enumerate(document.tables, 1):
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    for run in paragraph.runs:
                        if run.text.strip() and run.font.name and run.font.name != "Times New Roman":
                            issues.append({
                                "location": f"Таблица {idx}",
                                "code": "TABLE_FONT_MISMATCH",
                                "message": f"Шрифт «{run.font.name}», требуется Times New Roman",
                                "description": "Текст в таблицах — Times New Roman",
                                "severity": "medium",
                                "expected": "Times New Roman", "actual": run.font.name,
                            })
                            return issues
    return issues


# ═══════ 11. Лишние пробелы ═══════

def check_extra_spaces(document: DocxDocument) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    double_spaces = sum(len(re.findall(r"  +", p.text)) for p in document.paragraphs if p.text.strip())
    space_punct = sum(len(re.findall(r" +[,;.!?]", p.text)) for p in document.paragraphs if p.text.strip())
    if double_spaces > 0:
        issues.append({
            "location": "Документ в целом",
            "code": "DOUBLE_SPACES",
            "message": f"Двойных пробелов: {double_spaces}",
            "description": "В тексте не должно быть двойных пробелов",
            "severity": "low",
            "expected": "одинарные пробелы", "actual": f"{double_spaces}",
        })
    if space_punct > 0:
        issues.append({
            "location": "Документ в целом",
            "code": "SPACE_BEFORE_PUNCT",
            "message": f"Пробелов перед знаками препинания: {space_punct}",
            "description": "Перед запятой, точкой и т.д. пробел не ставится",
            "severity": "low",
            "expected": "без пробела", "actual": f"{space_punct}",
        })
    return issues


# ═══════ 12. Наличие оглавления ═══════

def check_table_of_contents(document: DocxDocument) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    has_toc = False
    for paragraph in document.paragraphs:
        text = paragraph.text.strip().lower()
        style_name = (paragraph.style.name or "").lower()
        if "toc" in style_name:
            has_toc = True
            break
        if text in ("содержание", "оглавление"):
            has_toc = True
            break
    body_xml = document.element.body.xml
    if "TOC" in body_xml:
        has_toc = True
    if not has_toc:
        issues.append({
            "location": "Документ в целом",
            "code": "NO_TABLE_OF_CONTENTS",
            "message": "Не найдено оглавление",
            "description": "В работе должно быть оглавление с номерами страниц",
            "severity": "low",
            "expected": "раздел «Содержание»", "actual": "не найдено",
        })
    return issues
