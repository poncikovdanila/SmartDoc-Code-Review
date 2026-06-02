"""Тесты для модуля проверки Python-кода."""
from pathlib import Path

import pytest

from app.checkers.code_checker import check_python_code


def _write(tmp_path: Path, name: str, content: str) -> Path:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


def test_clean_code_has_no_issues(tmp_path):
    """Чистый код по PEP 8 не должен порождать замечаний."""
    src = (
        '"""Demo module."""\n'
        "\n"
        "\n"
        "def add(a, b):\n"
        '    """Return sum."""\n'
        "    return a + b\n"
    )
    path = _write(tmp_path, "clean.py", src)
    report = check_python_code(path, "clean.py")

    assert report["file_type"] == "python"
    assert report["total_issues"] == 0
    assert report["summary"] == {"high": 0, "medium": 0, "low": 0}


def test_messy_code_finds_multiple_issues(tmp_path):
    """Грязный код должен порождать несколько замечаний."""
    src = (
        "import os,sys\n"  # E401: множественные импорты
        "x=1\n"  # E225: нет пробелов вокруг =
        "very_long_variable_name = 'a' * 200  # это очень длинная строка, превышающая лимит в 79 символов точно-точно\n"  # E501
    )
    path = _write(tmp_path, "messy.py", src)
    report = check_python_code(path, "messy.py")

    assert report["total_issues"] > 0
    codes = {issue["code"] for issue in report["issues"]}
    # Должны увидеть хотя бы эти коды
    assert "E401" in codes
    assert "E225" in codes
    assert "E501" in codes


def test_unused_import_is_high_severity(tmp_path):
    """Неиспользуемый импорт — это F401, должен иметь severity=high."""
    src = "import json\n\nprint('hello')\n"
    path = _write(tmp_path, "unused.py", src)
    report = check_python_code(path, "unused.py")

    f401_issues = [i for i in report["issues"] if i["code"] == "F401"]
    assert len(f401_issues) == 1
    assert f401_issues[0]["severity"] == "high"


def test_issues_sorted_by_line(tmp_path):
    """Список замечаний должен быть отсортирован по номерам строк."""
    src = (
        "import os\n"  # F401 на строке 1
        "x=1\n"  # E225 на строке 2
        "y=2\n"  # E225 на строке 3
    )
    path = _write(tmp_path, "sorted.py", src)
    report = check_python_code(path, "sorted.py")

    lines = [issue["line"] for issue in report["issues"]]
    assert lines == sorted(lines)


def test_report_includes_source(tmp_path):
    """Отчёт должен содержать исходный код для отображения контекста."""
    src = "x=1\n"
    path = _write(tmp_path, "src.py", src)
    report = check_python_code(path, "src.py")

    assert "source_lines" in report
    assert report["source_lines"] == ["x=1"]
