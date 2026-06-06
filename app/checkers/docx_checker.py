"""Модуль нормоконтроля документов .docx по требованиям АГУ (ФЦТиК).

Область применения: направление 09.03.02 «Информационные системы и технологии»,
факультет цифровых технологий и кибербезопасности, каф. ИТиК.
Инженерно-технический подход с ориентацией на ЕСКД.

Проверяемые параметры (см. docs/Требования_нормоконтроля_АГУ_ФЦТиК.md):
    * шрифт: Times New Roman, 14 пт
    * межстрочный интервал: 1.5
    * отступ первой строки абзаца: 1.25 см
    * поля страницы: левое 3 см, правое 1.5 см, верхнее и нижнее по 2 см
    * выравнивание текста по ширине
    * оформление заголовков (жирный, без точки)
    * нумерация страниц (наличие)
    * наличие оглавления
    * подписи к таблицам и рисункам
    * список литературы (наличие раздела)
    * гиперссылки (чёрный цвет, без подчёркивания)
    * цвет текста (чёрный)
    * лишние пробелы (двойные, перед знаками препинания)
    * пустые строки (не более одной подряд)
    * шрифт в таблицах (Times New Roman)
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from docx import Document
from docx.shared import Cm, Pt
from docx.document import Document as DocxDocument
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph

from app.checkers.docx_extras import (
    check_bibliography,
    check_figure_captions,
    check_table_captions,
    check_text_alignment,
    check_extra_blank_lines,
    check_headings,
    check_page_numbers,
    check_hyperlinks,
    check_text_color,
    check_table_formatting,
    check_extra_spaces,
    check_table_of_contents,
)

# Эталонные значения по ГОСТ/АГУ. Если в учебном заведении изменятся требования —
# меняем только здесь.
EXPECTED_FONT_NAME = "Times New Roman"
EXPECTED_FONT_SIZE_PT = 14.0
EXPECTED_LINE_SPACING = 1.5
EXPECTED_FIRST_LINE_INDENT_CM = 1.25
EXPECTED_MARGINS_CM = {
    "left": 3.0,
    "right": 1.5,
    "top": 2.0,
    "bottom": 2.0,
}

# Пресеты правил для разных учебных заведений
PRESETS: dict[str, dict[str, Any]] = {
    "agu": {
        "font_name": "Times New Roman",
        "font_size_pt": 14.0,
        "line_spacing": 1.5,
        "first_line_indent_cm": 1.25,
        "margins_cm": {"left": 3.0, "right": 1.5, "top": 2.0, "bottom": 2.0},
        "label": "АГУ (ГОСТ)",
    },
    "mgu": {
        "font_name": "Times New Roman",
        "font_size_pt": 14.0,
        "line_spacing": 1.5,
        "first_line_indent_cm": 1.25,
        "margins_cm": {"left": 3.0, "right": 1.0, "top": 2.0, "bottom": 2.0},
        "label": "МГУ",
    },
    "spbgu": {
        "font_name": "Times New Roman",
        "font_size_pt": 14.0,
        "line_spacing": 1.5,
        "first_line_indent_cm": 1.25,
        "margins_cm": {"left": 2.5, "right": 1.0, "top": 2.0, "bottom": 2.0},
        "label": "СПбГУ",
    },
    "hse": {
        "font_name": "Times New Roman",
        "font_size_pt": 14.0,
        "line_spacing": 1.5,
        "first_line_indent_cm": 1.25,
        "margins_cm": {"left": 3.0, "right": 1.5, "top": 2.0, "bottom": 2.0},
        "label": "ВШЭ",
    },
}


def _get_rules(custom_rules: dict[str, Any] | None = None) -> dict[str, Any]:
    """Возвращает правила проверки. Если передан пресет или кастом — используем их,
    иначе — дефолтные АГУ."""
    if custom_rules is None:
        return {
            "font_name": EXPECTED_FONT_NAME,
            "font_size_pt": EXPECTED_FONT_SIZE_PT,
            "line_spacing": EXPECTED_LINE_SPACING,
            "first_line_indent_cm": EXPECTED_FIRST_LINE_INDENT_CM,
            "margins_cm": dict(EXPECTED_MARGINS_CM),
            "alignment": "justify",
            "bib_name": "any",
            "checks": {
                "headings": True,
                "pageNumbers": True,
                "toc": True,
                "bibliography": True,
                "hyperlinks": True,
                "textColor": True,
                "tables": True,
                "spaces": True,
                "blankLines": True,
            },
        }

    # Если указан пресет — берём его как базу
    preset_name = custom_rules.get("preset")
    if preset_name and preset_name in PRESETS:
        base = dict(PRESETS[preset_name])
        base["margins_cm"] = dict(base["margins_cm"])
    else:
        base = _get_rules(None)

    # Перезаписываем отдельные поля, если переданы
    if "font_name" in custom_rules:
        name = str(custom_rules["font_name"]).strip()
        if name:
            base["font_name"] = name
    if "font_size_pt" in custom_rules:
        base["font_size_pt"] = _clamp(float(custom_rules["font_size_pt"]), 6, 72)
    if "line_spacing" in custom_rules:
        base["line_spacing"] = _clamp(float(custom_rules["line_spacing"]), 0.5, 5.0)
    if "first_line_indent_cm" in custom_rules:
        base["first_line_indent_cm"] = _clamp(float(custom_rules["first_line_indent_cm"]), 0, 10)
    if "margins_cm" in custom_rules:
        for side in ("left", "right", "top", "bottom"):
            if side in custom_rules["margins_cm"]:
                base["margins_cm"][side] = _clamp(float(custom_rules["margins_cm"][side]), 0, 15)
    if "alignment" in custom_rules:
        base["alignment"] = custom_rules["alignment"]
    if "bib_name" in custom_rules:
        base["bib_name"] = custom_rules["bib_name"]
    if "checks" in custom_rules:
        for key, val in custom_rules["checks"].items():
            base["checks"][key] = bool(val)
    # Обратная совместимость
    if "check_page_numbers" in custom_rules:
        base["checks"]["pageNumbers"] = bool(custom_rules["check_page_numbers"])
    return base


def _clamp(value: float, lo: float, hi: float) -> float:
    """Ограничивает значение диапазоном [lo, hi]."""
    return max(lo, min(hi, value))

# Точность сравнения для значений с плавающей точкой. В .docx размеры обычно
# хранятся точно, но при импорте из других редакторов бывают отклонения.
TOLERANCE_CM = 0.05  # 0.5 мм
TOLERANCE_PT = 0.5
TOLERANCE_SPACING = 0.05


def _emu_to_cm(emu_value: int | None) -> float | None:
    """Переводит EMU (английские метрические единицы) в сантиметры."""
    if emu_value is None:
        return None
    # 1 см = 360000 EMU
    return emu_value / 360000


def _resolve_font_name(paragraph: Paragraph, document: DocxDocument) -> str | None:
    """Определяет фактическое имя шрифта абзаца.

    Логика «как в Word»: run → стиль абзаца → стиль Normal →
    docDefaults (XML) → тема документа. Если ни на одном уровне
    не задано — None.
    """
    # 1. Уровень run (берём первый непустой run)
    for run in paragraph.runs:
        if run.font.name:
            return run.font.name
    # 2. Уровень стиля абзаца
    style = paragraph.style
    while style is not None:
        if style.font and style.font.name:
            return style.font.name
        style = style.base_style
    # 3. Стиль документа по умолчанию
    try:
        default_font = document.styles["Normal"].font
        if default_font.name:
            return default_font.name
    except KeyError:
        pass
    # 4. docDefaults в XML (w:styles/w:docDefaults/w:rPrDefault/w:rPr/w:rFonts)
    try:
        styles_el = document.styles.element
        doc_defaults = styles_el.find(qn("w:docDefaults"))
        if doc_defaults is not None:
            rpr_default = doc_defaults.find(qn("w:rPrDefault"))
            if rpr_default is not None:
                rpr = rpr_default.find(qn("w:rPr"))
                if rpr is not None:
                    rfonts = rpr.find(qn("w:rFonts"))
                    if rfonts is not None:
                        for attr in ("w:ascii", "w:hAnsi", "w:cs"):
                            val = rfonts.get(qn(attr))
                            if val:
                                return val
    except Exception:
        pass
    return None


def _resolve_font_size_pt(paragraph: Paragraph, document: DocxDocument) -> float | None:
    """Аналогично имени шрифта — определяет фактический размер в пунктах."""
    for run in paragraph.runs:
        if run.font.size is not None:
            return run.font.size.pt
    style = paragraph.style
    while style is not None:
        if style.font and style.font.size is not None:
            return style.font.size.pt
        style = style.base_style
    try:
        default_size = document.styles["Normal"].font.size
        if default_size is not None:
            return default_size.pt
    except KeyError:
        pass
    # docDefaults в XML (w:sz)
    try:
        styles_el = document.styles.element
        doc_defaults = styles_el.find(qn("w:docDefaults"))
        if doc_defaults is not None:
            rpr_default = doc_defaults.find(qn("w:rPrDefault"))
            if rpr_default is not None:
                rpr = rpr_default.find(qn("w:rPr"))
                if rpr is not None:
                    sz = rpr.find(qn("w:sz"))
                    if sz is not None:
                        val = sz.get(qn("w:val"))
                        if val:
                            return int(val) / 2  # half-points → points
    except Exception:
        pass
    return None


def _resolve_line_spacing(paragraph: Paragraph, document: DocxDocument = None) -> float | None:
    """Возвращает множитель межстрочного интервала.
    Если нигде не задан — возвращает 1.0 (дефолт Word)."""
    pf = paragraph.paragraph_format
    spacing = pf.line_spacing
    if spacing is None:
        style = paragraph.style
        while style is not None:
            sp = style.paragraph_format.line_spacing
            if sp is not None:
                spacing = sp
                break
            style = style.base_style
    if spacing is None and document is not None:
        try:
            normal_sp = document.styles["Normal"].paragraph_format.line_spacing
            if normal_sp is not None:
                spacing = normal_sp
        except (KeyError, AttributeError):
            pass
    if spacing is None:
        return 1.0  # Word default: одинарный интервал
    if hasattr(spacing, "pt"):
        return None  # точный интервал — отдельная проверка
    return float(spacing)


def _resolve_first_line_indent_cm(paragraph: Paragraph, document: DocxDocument = None) -> float | None:
    """Отступ первой строки абзаца в сантиметрах.
    Если нигде не задан — возвращает 0.0 (дефолт Word)."""
    pf = paragraph.paragraph_format
    indent = pf.first_line_indent
    if indent is None:
        style = paragraph.style
        while style is not None:
            ind = style.paragraph_format.first_line_indent
            if ind is not None:
                indent = ind
                break
            style = style.base_style
    if indent is None and document is not None:
        try:
            normal_ind = document.styles["Normal"].paragraph_format.first_line_indent
            if normal_ind is not None:
                indent = normal_ind
        except (KeyError, AttributeError):
            pass
    if indent is None:
        return 0.0  # Word default: нет отступа
    return indent.cm
    if indent is None:
        return None
    return indent.cm


def _is_text_paragraph(paragraph: Paragraph) -> bool:
    """Проверяемые абзацы — только содержательный текст. Пустые, заголовки и
    подписи к таблицам не проверяем (для них требования другие).
    """
    text = paragraph.text.strip()
    if not text:
        return False
    style_name = (paragraph.style.name or "").lower()
    # Заголовки оформляются по другим правилам
    if "heading" in style_name or "заголов" in style_name:
        return False
    # Подписи, оглавление, нумерованные списки — отдельная история
    if "caption" in style_name or "toc" in style_name or "список" in style_name:
        return False
    return True


def check_docx_document(file_path: Path, original_filename: str,
                        custom_rules: dict[str, Any] | None = None) -> dict[str, Any]:
    """Проверяет .docx-файл и возвращает структурированный отчёт.

    Args:
        file_path: путь к временной копии загруженного файла.
        original_filename: исходное имя файла.
        custom_rules: пользовательские правила проверки (опционально).

    Возвращает тот же формат, что и check_python_code, чтобы фронтенд
    обрабатывал оба типа единообразно.
    """
    rules = _get_rules(custom_rules)
    r_font = rules["font_name"]
    r_size = rules["font_size_pt"]
    r_spacing = rules["line_spacing"]
    r_indent = rules["first_line_indent_cm"]
    r_margins = rules["margins_cm"]

    issues: list[dict[str, Any]] = []
    summary = {"high": 0, "medium": 0, "low": 0}

    try:
        document = Document(file_path)
    except Exception as exc:
        return {
            "filename": original_filename,
            "file_type": "docx",
            "total_issues": 0,
            "summary": summary,
            "issues": [],
            "error": f"Не удалось открыть документ: {exc}",
            "source_lines": [],
        }

    # ───── 1. Проверка полей страницы ─────
    for section_index, section in enumerate(document.sections, start=1):
        margins_actual = {
            "left": _emu_to_cm(section.left_margin),
            "right": _emu_to_cm(section.right_margin),
            "top": _emu_to_cm(section.top_margin),
            "bottom": _emu_to_cm(section.bottom_margin),
        }
        margin_labels = {
            "left": "левое",
            "right": "правое",
            "top": "верхнее",
            "bottom": "нижнее",
        }
        for side, expected in r_margins.items():
            actual = margins_actual[side]
            if actual is None:
                issues.append(
                    {
                        "location": f"Раздел {section_index}, поля страницы",
                        "code": "MARGIN_MISSING",
                        "message": f"Не задано {margin_labels[side]} поле страницы",
                        "description": (
                            f"Требуется {margin_labels[side]} поле = {expected} см "
                            "(ГОСТ/АГУ)"
                        ),
                        "severity": "high",
                        "expected": f"{expected} см",
                        "actual": "не задано",
                    }
                )
                summary["high"] += 1
                continue
            if abs(actual - expected) > TOLERANCE_CM:
                issues.append(
                    {
                        "location": f"Раздел {section_index}, поля страницы",
                        "code": "MARGIN_MISMATCH",
                        "message": (
                            f"{margin_labels[side].capitalize()} поле = {actual:.2f} см, "
                            f"требуется {expected} см"
                        ),
                        "description": (
                            "Поля страницы по ГОСТ/АГУ: левое 3 см, правое 1.5 см, "
                            "верхнее и нижнее по 2 см"
                        ),
                        "severity": "high",
                        "expected": f"{expected} см",
                        "actual": f"{actual:.2f} см",
                    }
                )
                summary["high"] += 1

    # ───── 2. Проверка абзацев ─────
    paragraph_number = 0
    for paragraph in document.paragraphs:
        if not _is_text_paragraph(paragraph):
            continue
        paragraph_number += 1
        # Превью первых 60 символов абзаца — чтобы пользователь нашёл место в документе
        preview = paragraph.text.strip()
        if len(preview) > 60:
            preview = preview[:60] + "…"
        location = f"Абзац {paragraph_number}: «{preview}»"

        # 2.1. Шрифт
        font_name = _resolve_font_name(paragraph, document)
        if font_name is None:
            issues.append(
                {
                    "location": location,
                    "code": "FONT_NOT_SET",
                    "message": "Шрифт не задан явно",
                    "description": (
                        f"Требуется явное указание шрифта {r_font}"
                    ),
                    "severity": "medium",
                    "expected": r_font,
                    "actual": "не задан",
                }
            )
            summary["medium"] += 1
        elif font_name != r_font:
            issues.append(
                {
                    "location": location,
                    "code": "FONT_MISMATCH",
                    "message": f"Шрифт «{font_name}», требуется «{r_font}»",
                    "description": f"Основной шрифт работы — {r_font}",
                    "severity": "high",
                    "expected": r_font,
                    "actual": font_name,
                }
            )
            summary["high"] += 1

        # 2.2. Размер шрифта
        font_size = _resolve_font_size_pt(paragraph, document)
        if font_size is None:
            issues.append(
                {
                    "location": location,
                    "code": "FONT_SIZE_NOT_SET",
                    "message": "Размер шрифта не задан явно",
                    "description": f"Требуется размер {r_size} пт",
                    "severity": "medium",
                    "expected": f"{r_size} пт",
                    "actual": "не задан",
                }
            )
            summary["medium"] += 1
        elif abs(font_size - r_size) > TOLERANCE_PT:
            issues.append(
                {
                    "location": location,
                    "code": "FONT_SIZE_MISMATCH",
                    "message": (
                        f"Размер шрифта {font_size:.1f} пт, "
                        f"требуется {r_size} пт"
                    ),
                    "description": f"Основной текст работы оформляется кеглем {r_size:.0f}",
                    "severity": "high",
                    "expected": f"{r_size} пт",
                    "actual": f"{font_size:.1f} пт",
                }
            )
            summary["high"] += 1

        # 2.3. Межстрочный интервал
        line_spacing = _resolve_line_spacing(paragraph, document)
        if line_spacing is None:
            issues.append(
                {
                    "location": location,
                    "code": "LINE_SPACING_NOT_SET",
                    "message": "Межстрочный интервал не задан или задан как точное значение",
                    "description": (
                        f"Требуется множитель {r_spacing} (полуторный)"
                    ),
                    "severity": "medium",
                    "expected": f"{r_spacing}",
                    "actual": "не задан/точный",
                }
            )
            summary["medium"] += 1
        elif abs(line_spacing - r_spacing) > TOLERANCE_SPACING:
            issues.append(
                {
                    "location": location,
                    "code": "LINE_SPACING_MISMATCH",
                    "message": (
                        f"Межстрочный интервал {line_spacing:.2f}, "
                        f"требуется {r_spacing}"
                    ),
                    "description": (
                        f"Основной текст оформляется интервалом {r_spacing}"
                    ),
                    "severity": "high",
                    "expected": f"{r_spacing}",
                    "actual": f"{line_spacing:.2f}",
                }
            )
            summary["high"] += 1

        # 2.4. Отступ первой строки
        indent = _resolve_first_line_indent_cm(paragraph, document)
        if indent is None:
            issues.append(
                {
                    "location": location,
                    "code": "INDENT_NOT_SET",
                    "message": "Отступ первой строки не задан",
                    "description": (
                        f"Требуется отступ первой строки {r_indent} см"
                    ),
                    "severity": "medium",
                    "expected": f"{r_indent} см",
                    "actual": "не задан",
                }
            )
            summary["medium"] += 1
        elif abs(indent - r_indent) > TOLERANCE_CM:
            issues.append(
                {
                    "location": location,
                    "code": "INDENT_MISMATCH",
                    "message": (
                        f"Отступ первой строки {indent:.2f} см, "
                        f"требуется {r_indent} см"
                    ),
                    "description": f"Красная строка — {r_indent} см",
                    "severity": "medium",
                    "expected": f"{r_indent} см",
                    "actual": f"{indent:.2f} см",
                }
            )
            summary["medium"] += 1

    # ───── 3. Расширенные проверки ─────
    extra_issues: list[dict[str, Any]] = []
    checks = rules.get("checks", {})

    extra_issues.extend(check_table_captions(document))
    extra_issues.extend(check_figure_captions(document))

    if checks.get("bibliography", True):
        extra_issues.extend(check_bibliography(document))
    if rules.get("alignment", "justify") != "any":
        extra_issues.extend(check_text_alignment(document))
    if checks.get("blankLines", True):
        extra_issues.extend(check_extra_blank_lines(document))
    if checks.get("headings", True):
        extra_issues.extend(check_headings(document))
    if checks.get("pageNumbers", True):
        extra_issues.extend(check_page_numbers(document))
    if checks.get("hyperlinks", True):
        extra_issues.extend(check_hyperlinks(document))
    if checks.get("textColor", True):
        extra_issues.extend(check_text_color(document))
    if checks.get("tables", True):
        extra_issues.extend(check_table_formatting(document))
    if checks.get("spaces", True):
        extra_issues.extend(check_extra_spaces(document))
    if checks.get("toc", True):
        extra_issues.extend(check_table_of_contents(document))
    for issue in extra_issues:
        summary[issue["severity"]] += 1
    issues.extend(extra_issues)

    # Вердикт вместо процентов
    if not issues:
        verdict = "good"
    elif summary["high"] == 0:
        verdict = "ok"
    else:
        verdict = "bad"

    return {
        "filename": original_filename,
        "file_type": "docx",
        "total_issues": len(issues),
        "summary": summary,
        "verdict": verdict,
        "issues": issues,
        "paragraphs_checked": paragraph_number,
        "source_lines": [],
    }
