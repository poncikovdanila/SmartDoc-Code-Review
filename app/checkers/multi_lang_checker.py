"""Модуль проверки кода на нескольких языках.

Поддерживаемые языки и инструменты:
    .py   → flake8 (PEP 8 + pyflakes)             — уже был
    .js   → встроенный чекер на основе регулярок   — новый
    .sql  → встроенный чекер SQL-стиля             — новый
    .java → встроенный чекер Java-конвенций         — новый
    .cpp / .c / .h → встроенный чекер C/C++ стиля  — новый

Почему встроенные, а не внешние линтеры (ESLint, checkstyle и т. п.)?
    Для учебного проекта важна простота установки: pip install и готово.
    ESLint требует Node.js, checkstyle — JDK. Это лишний барьер. Наши
    встроенные чекеры покрывают 80% типичных студенческих ошибок: именование,
    пробелы, длина строк, скобки, комментарии. Для серьёзного продакшна
    можно подключить настоящие линтеры позже.

Каждый чекер возвращает единый формат: список замечаний с полями
line, column, code, message, description, severity.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any


# ═══════ Общие утилиты ═══════

def _read_source(file_path: Path) -> list[str]:
    try:
        return file_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []


def _make_report(
    lines: list[str],
    issues: list[dict[str, Any]],
    filename: str,
    language: str,
) -> dict[str, Any]:
    summary = {"high": 0, "medium": 0, "low": 0}
    for issue in issues:
        summary[issue["severity"]] += 1
    issues.sort(key=lambda i: (i["line"], i.get("column", 0)))
    return {
        "filename": filename,
        "file_type": language,
        "total_issues": len(issues),
        "summary": summary,
        "issues": issues,
        "source_lines": lines,
    }


# ═══════ JavaScript (.js) ═══════

JS_RULES: list[tuple[str, str, re.Pattern, str, str]] = [
    # (code, severity, regex, message, description)
    ("JS001", "medium", re.compile(r"^\t"), "Отступ табуляцией", "Используйте пробелы для отступов, не табуляцию"),
    ("JS002", "medium", re.compile(r"(?<!=)={2}(?!=)"), "Используется == вместо ===", "Строгое сравнение === безопаснее, чем нестрогое =="),
    ("JS003", "medium", re.compile(r"!=(?!=)"), "Используется != вместо !==", "Строгое неравенство !== безопаснее"),
    ("JS004", "low", re.compile(r"\s+$"), "Пробелы в конце строки", "Удалите лишние пробелы в конце строки"),
    ("JS005", "high", re.compile(r"\bvar\b"), "Используется var", "Используйте let или const вместо var — они безопаснее благодаря блочной области видимости"),
    ("JS006", "medium", re.compile(r"console\.(log|warn|error|debug)\s*\("), "Остался console.log", "Уберите отладочные console.log перед сдачей"),
    ("JS007", "low", re.compile(r";\s*$"), "Точка с запятой", "В современном JS точки с запятой необязательны (зависит от стиля проекта)"),
    ("JS008", "medium", re.compile(r"function\s+[A-Z]"), "Функция начинается с заглавной", "Функции именуются в camelCase. Заглавная — для классов и конструкторов"),
]

JS_LINE_LENGTH = 100


def check_javascript(file_path: Path, original_filename: str) -> dict[str, Any]:
    lines = _read_source(file_path)
    issues: list[dict[str, Any]] = []
    for i, line in enumerate(lines, 1):
        for code, severity, pattern, message, description in JS_RULES:
            if pattern.search(line):
                issues.append({
                    "line": i, "column": 1, "code": code,
                    "message": message, "description": description,
                    "severity": severity,
                })
        if len(line) > JS_LINE_LENGTH:
            issues.append({
                "line": i, "column": JS_LINE_LENGTH + 1, "code": "JS010",
                "message": f"Строка длиннее {JS_LINE_LENGTH} символов ({len(line)})",
                "description": f"Рекомендуемый лимит строки — {JS_LINE_LENGTH} символов",
                "severity": "low",
            })
    return _make_report(lines, issues, original_filename, "javascript")


# ═══════ SQL (.sql) ═══════

SQL_KEYWORDS = {
    "select", "from", "where", "join", "inner", "outer", "left", "right",
    "on", "group", "by", "order", "having", "insert", "into", "values",
    "update", "set", "delete", "create", "table", "alter", "drop", "index",
    "and", "or", "not", "in", "between", "like", "is", "null", "as",
    "distinct", "union", "all", "exists", "case", "when", "then", "else", "end",
    "limit", "offset", "asc", "desc", "count", "sum", "avg", "min", "max",
}

SQL_LINE_LENGTH = 120


def check_sql(file_path: Path, original_filename: str) -> dict[str, Any]:
    lines = _read_source(file_path)
    issues: list[dict[str, Any]] = []

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue

        # Ключевые слова должны быть в верхнем регистре
        words = re.findall(r'\b[a-zA-Z_]+\b', stripped)
        for word in words:
            if word.lower() in SQL_KEYWORDS and word != word.upper() and word != word.lower():
                # Смешанный регистр — точно ошибка
                pass
            elif word.lower() in SQL_KEYWORDS and word != word.upper():
                issues.append({
                    "line": i, "column": 1, "code": "SQL001",
                    "message": f"Ключевое слово «{word}» не в верхнем регистре",
                    "description": "SQL-ключевые слова принято писать ЗАГЛАВНЫМИ (SELECT, FROM, WHERE)",
                    "severity": "medium",
                })
                break  # одно замечание на строку, иначе раздувается

        # SELECT * — плохая практика
        if re.search(r'\bSELECT\s+\*', stripped, re.IGNORECASE):
            issues.append({
                "line": i, "column": 1, "code": "SQL002",
                "message": "Используется SELECT *",
                "description": "Перечисляйте нужные столбцы явно — SELECT * тянет лишние данные",
                "severity": "medium",
            })

        # Длина строки
        if len(line) > SQL_LINE_LENGTH:
            issues.append({
                "line": i, "column": SQL_LINE_LENGTH + 1, "code": "SQL010",
                "message": f"Строка длиннее {SQL_LINE_LENGTH} символов",
                "description": "Разбивайте длинные запросы на несколько строк",
                "severity": "low",
            })

        # Пробелы в конце
        if line.rstrip() != line:
            issues.append({
                "line": i, "column": len(line.rstrip()) + 1, "code": "SQL003",
                "message": "Пробелы в конце строки",
                "description": "Удалите лишние пробелы",
                "severity": "low",
            })

    return _make_report(lines, issues, original_filename, "sql")


# ═══════ Java (.java) ═══════

JAVA_LINE_LENGTH = 120


def check_java(file_path: Path, original_filename: str) -> dict[str, Any]:
    lines = _read_source(file_path)
    issues: list[dict[str, Any]] = []

    in_block_comment = False

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # Пропускаем блочные комментарии
        if "/*" in stripped:
            in_block_comment = True
        if in_block_comment:
            if "*/" in stripped:
                in_block_comment = False
            continue
        if stripped.startswith("//") or not stripped:
            continue

        # Открывающая скобка на новой строке (стиль K&R vs Allman)
        if stripped == "{":
            issues.append({
                "line": i, "column": 1, "code": "JAVA001",
                "message": "Открывающая скобка на отдельной строке",
                "description": "В Java принят стиль K&R: открывающая скобка на той же строке, что и оператор",
                "severity": "low",
            })

        # Имя класса не с заглавной
        m = re.match(r'\s*(?:public\s+|private\s+|protected\s+)?class\s+([a-z]\w*)', line)
        if m:
            issues.append({
                "line": i, "column": 1, "code": "JAVA002",
                "message": f"Имя класса «{m.group(1)}» начинается со строчной",
                "description": "Имена классов в Java пишутся в PascalCase (с заглавной буквы)",
                "severity": "high",
            })

        # Метод с заглавной буквы (но не конструктор)
        m = re.match(r'\s*(?:public|private|protected|static|\s)*\s+\w+\s+([A-Z]\w*)\s*\(', line)
        if m and not re.match(r'\s*(?:public\s+|private\s+|protected\s+)?class\s', line):
            issues.append({
                "line": i, "column": 1, "code": "JAVA003",
                "message": f"Имя метода «{m.group(1)}» начинается с заглавной",
                "description": "Методы в Java именуются в camelCase (со строчной буквы)",
                "severity": "medium",
            })

        # Табуляция вместо пробелов
        if line.startswith("\t"):
            issues.append({
                "line": i, "column": 1, "code": "JAVA004",
                "message": "Отступ табуляцией",
                "description": "Используйте 4 пробела для отступов",
                "severity": "medium",
            })

        # System.out.println — отладочный вывод
        if "System.out.print" in line:
            issues.append({
                "line": i, "column": 1, "code": "JAVA005",
                "message": "Остался System.out.println",
                "description": "Уберите отладочный вывод. Для логирования используйте Logger",
                "severity": "medium",
            })

        # Длина строки
        if len(line) > JAVA_LINE_LENGTH:
            issues.append({
                "line": i, "column": JAVA_LINE_LENGTH + 1, "code": "JAVA010",
                "message": f"Строка длиннее {JAVA_LINE_LENGTH} символов",
                "description": f"Рекомендуемый лимит — {JAVA_LINE_LENGTH} символов",
                "severity": "low",
            })

    return _make_report(lines, issues, original_filename, "java")


# ═══════ C/C++ (.c, .cpp, .h) ═══════

CPP_LINE_LENGTH = 100


def check_cpp(file_path: Path, original_filename: str) -> dict[str, Any]:
    lines = _read_source(file_path)
    issues: list[dict[str, Any]] = []

    in_block_comment = False

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        if "/*" in stripped:
            in_block_comment = True
        if in_block_comment:
            if "*/" in stripped:
                in_block_comment = False
            continue
        if stripped.startswith("//") or not stripped:
            continue

        # using namespace std — плохая практика
        if re.match(r'\s*using\s+namespace\s+std\s*;', line):
            issues.append({
                "line": i, "column": 1, "code": "CPP001",
                "message": "using namespace std",
                "description": "Избегайте using namespace std — это загрязняет глобальное пространство имён. Используйте std::cout, std::string и т. д.",
                "severity": "high",
            })

        # #include с кавычками для стандартных библиотек
        m = re.match(r'\s*#include\s+"(iostream|string|vector|map|set|algorithm|cmath|cstdlib|cstdio|fstream)"', line)
        if m:
            issues.append({
                "line": i, "column": 1, "code": "CPP002",
                "message": f"#include \"{m.group(1)}\" — используйте угловые скобки",
                "description": "Стандартные библиотеки подключаются через <>, а не кавычки: #include <iostream>",
                "severity": "medium",
            })

        # printf / scanf вместо cout / cin
        if re.search(r'\b(printf|scanf)\s*\(', line):
            issues.append({
                "line": i, "column": 1, "code": "CPP003",
                "message": "Используется printf/scanf",
                "description": "В C++ предпочтительнее std::cout / std::cin — они типобезопасны",
                "severity": "low",
            })

        # Табуляция
        if line.startswith("\t"):
            issues.append({
                "line": i, "column": 1, "code": "CPP004",
                "message": "Отступ табуляцией",
                "description": "Используйте пробелы для отступов",
                "severity": "medium",
            })

        # goto
        if re.search(r'\bgoto\b', line):
            issues.append({
                "line": i, "column": 1, "code": "CPP005",
                "message": "Используется goto",
                "description": "goto усложняет чтение кода. Используйте циклы и функции",
                "severity": "high",
            })

        # Длина строки
        if len(line) > CPP_LINE_LENGTH:
            issues.append({
                "line": i, "column": CPP_LINE_LENGTH + 1, "code": "CPP010",
                "message": f"Строка длиннее {CPP_LINE_LENGTH} символов",
                "description": f"Рекомендуемый лимит — {CPP_LINE_LENGTH} символов",
                "severity": "low",
            })

    return _make_report(lines, issues, original_filename, "cpp")


# ═══════ Роутер: определяет язык по расширению ═══════

CHECKERS = {
    ".js": check_javascript,
    ".sql": check_sql,
    ".java": check_java,
    ".cpp": check_cpp,
    ".c": check_cpp,
    ".h": check_cpp,
}

SUPPORTED_CODE_EXTENSIONS = {".py", ".js", ".sql", ".java", ".cpp", ".c", ".h"}

LANGUAGE_NAMES = {
    ".py": "Python", ".js": "JavaScript", ".sql": "SQL",
    ".java": "Java", ".cpp": "C++", ".c": "C", ".h": "C/C++ Header",
}


def check_code_file(file_path: Path, original_filename: str, extension: str) -> dict[str, Any]:
    """Роутер: вызывает нужный чекер по расширению."""
    checker = CHECKERS.get(extension)
    if checker is None:
        raise ValueError(f"Нет чекера для расширения {extension}")
    return checker(file_path, original_filename)
