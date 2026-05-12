"""Тесты для модуля автоисправления Python-кода."""
from app.checkers.code_fixer import autofix_python_code


def test_fixes_spacing():
    """autopep8 должен добавить пробелы вокруг операторов."""
    result = autofix_python_code("x=1\ny=2\n")
    assert "x = 1" in result["fixed_code"]
    assert result["changed"] is True


def test_clean_code_unchanged():
    """Чистый код не должен меняться."""
    src = "x = 1\n"
    result = autofix_python_code(src)
    assert result["fixed_code"] == src
    assert result["changed"] is False


def test_removes_unused_imports():
    """autoflake должен удалить неиспользуемые импорты."""
    result = autofix_python_code("import os, sys\nprint('hello')\n")
    assert result["changed"] is True
    # os и sys не используются — autoflake удаляет оба
    assert "import os" not in result["fixed_code"]
    assert "import sys" not in result["fixed_code"]
    assert "print" in result["fixed_code"]


def test_result_structure():
    """Результат содержит все нужные поля."""
    result = autofix_python_code("x=1\n")
    assert "fixed_code" in result
    assert "original_lines" in result
    assert "fixed_lines" in result
    assert "changed" in result
    assert isinstance(result["original_lines"], int)
