"""40 тестов проверки различных Python-файлов.

Каждый тест создаёт .py файл с определённым паттерном ошибок (или без них)
и проверяет, что code_checker и code_fixer реагируют корректно.
"""
from pathlib import Path

import pytest

from app.checkers.code_checker import check_python_code
from app.checkers.code_fixer import autofix_python_code


def _check(tmp_path: Path, code: str, filename: str = "test.py") -> dict:
    p = tmp_path / filename
    p.write_text(code, encoding="utf-8")
    return check_python_code(p, filename)


def _fix(code: str) -> dict:
    return autofix_python_code(code)


# ═══════ Чистый код (0 ошибок) ═══════

class TestCleanCode:
    def test_empty_file(self, tmp_path):
        r = _check(tmp_path, "")
        assert r["total_issues"] == 0

    def test_single_assignment(self, tmp_path):
        r = _check(tmp_path, "x = 1\n")
        assert r["total_issues"] == 0

    def test_proper_function(self, tmp_path):
        code = 'def greet(name):\n    return f"Hello, {name}"\n'
        r = _check(tmp_path, code)
        assert r["total_issues"] == 0

    def test_proper_class(self, tmp_path):
        code = (
            "class Calculator:\n"
            "    def add(self, a, b):\n"
            "        return a + b\n"
        )
        r = _check(tmp_path, code)
        assert r["total_issues"] == 0

    def test_proper_imports(self, tmp_path):
        code = "import os\nimport sys\n\n\nprint(os.getcwd(), sys.argv)\n"
        r = _check(tmp_path, code)
        assert r["total_issues"] == 0


# ═══════ Ошибки отступов (E1xx) ═══════

class TestIndentation:
    def test_wrong_indent_2_spaces(self, tmp_path):
        code = "def f():\n  return 1\n"
        r = _check(tmp_path, code)
        codes = {i["code"] for i in r["issues"]}
        assert codes & {"E111", "E117", "E114"}, f"Ожидалась ошибка отступа, получили: {codes}"

    def test_tab_indent(self, tmp_path):
        code = "def f():\n\treturn 1\n"
        r = _check(tmp_path, code)
        codes = {i["code"] for i in r["issues"]}
        assert codes & {"W191", "E101"}, f"Ожидалась ошибка табуляции, получили: {codes}"

    def test_mixed_indent(self, tmp_path):
        code = "def f():\n    x = 1\n\ty = 2\n"
        r = _check(tmp_path, code)
        assert r["total_issues"] > 0


# ═══════ Пробелы (E2xx) ═══════

class TestWhitespace:
    def test_missing_spaces_around_operator(self, tmp_path):
        code = "x=1+2\n"
        r = _check(tmp_path, code)
        codes = {i["code"] for i in r["issues"]}
        assert "E225" in codes

    def test_extra_space_after_bracket(self, tmp_path):
        code = "x = ( 1 + 2)\n"
        r = _check(tmp_path, code)
        codes = {i["code"] for i in r["issues"]}
        assert "E201" in codes

    def test_missing_space_after_comma(self, tmp_path):
        code = "x = [1,2,3]\n"
        r = _check(tmp_path, code)
        codes = {i["code"] for i in r["issues"]}
        assert "E231" in codes

    def test_trailing_whitespace(self, tmp_path):
        code = "x = 1   \n"
        r = _check(tmp_path, code)
        codes = {i["code"] for i in r["issues"]}
        assert "W291" in codes


# ═══════ Пустые строки (E3xx) ═══════

class TestBlankLines:
    def test_missing_blank_lines_between_functions(self, tmp_path):
        code = "def f():\n    pass\ndef g():\n    pass\n"
        r = _check(tmp_path, code)
        codes = {i["code"] for i in r["issues"]}
        assert "E302" in codes

    def test_too_many_blank_lines(self, tmp_path):
        code = "x = 1\n\n\n\n\ny = 2\n"
        r = _check(tmp_path, code)
        codes = {i["code"] for i in r["issues"]}
        assert "E303" in codes


# ═══════ Импорты (E4xx, F4xx) ═══════

class TestImports:
    def test_multiple_imports_one_line(self, tmp_path):
        code = "import os, sys\n\nprint(os.getcwd(), sys.argv)\n"
        r = _check(tmp_path, code)
        codes = {i["code"] for i in r["issues"]}
        assert "E401" in codes

    def test_unused_import(self, tmp_path):
        code = "import os\n\nx = 1\n"
        r = _check(tmp_path, code)
        codes = {i["code"] for i in r["issues"]}
        assert "F401" in codes

    def test_unused_import_is_high_severity(self, tmp_path):
        code = "import os\n\nx = 1\n"
        r = _check(tmp_path, code)
        f401 = [i for i in r["issues"] if i["code"] == "F401"]
        assert f401[0]["severity"] == "high"

    def test_multiple_unused_imports(self, tmp_path):
        code = "import os\nimport sys\nimport json\n\nx = 1\n"
        r = _check(tmp_path, code)
        f401 = [i for i in r["issues"] if i["code"] == "F401"]
        assert len(f401) == 3


# ═══════ Длина строки (E501) ═══════

class TestLineLength:
    def test_line_over_79_chars(self, tmp_path):
        code = f"x = '{'a' * 80}'\n"
        r = _check(tmp_path, code)
        codes = {i["code"] for i in r["issues"]}
        assert "E501" in codes

    def test_line_exactly_79_chars(self, tmp_path):
        code = "x" * 79 + "\n"
        r = _check(tmp_path, code)
        e501 = [i for i in r["issues"] if i["code"] == "E501"]
        assert len(e501) == 0


# ═══════ Переменные и имена (F8xx) ═══════

class TestNames:
    def test_undefined_name(self, tmp_path):
        code = "print(undefined_variable)\n"
        r = _check(tmp_path, code)
        codes = {i["code"] for i in r["issues"]}
        assert "F821" in codes

    def test_redefined_unused(self, tmp_path):
        code = "x = 1\nx = 2\nprint(x)\n"
        r = _check(tmp_path, code)
        f841 = [i for i in r["issues"] if i["code"] == "F841"]
        # F841 только если переменная вообще не используется
        # Здесь x используется в print, поэтому F841 не должно быть
        assert len(f841) == 0

    def test_unused_variable(self, tmp_path):
        code = "def f():\n    result = 42\n    return None\n"
        r = _check(tmp_path, code)
        f841 = [i for i in r["issues"] if i["code"] == "F841"]
        assert len(f841) == 1


# ═══════ Структура отчёта ═══════

class TestReportStructure:
    def test_has_required_fields(self, tmp_path):
        r = _check(tmp_path, "x = 1\n")
        assert "filename" in r
        assert "file_type" in r
        assert r["file_type"] == "python"
        assert "total_issues" in r
        assert "summary" in r
        assert "issues" in r
        assert "source_lines" in r

    def test_summary_matches_total(self, tmp_path):
        code = "import os\nimport sys\nx=1\n"
        r = _check(tmp_path, code)
        s = r["summary"]
        assert s["high"] + s["medium"] + s["low"] == r["total_issues"]

    def test_source_lines_match_file(self, tmp_path):
        code = "x = 1\ny = 2\nz = 3\n"
        r = _check(tmp_path, code)
        assert r["source_lines"] == ["x = 1", "y = 2", "z = 3"]

    def test_issues_sorted_by_line(self, tmp_path):
        code = "import os\nimport sys\nx=1+2\ny=3\n"
        r = _check(tmp_path, code)
        lines = [i["line"] for i in r["issues"]]
        assert lines == sorted(lines)

    def test_issue_has_code_and_description(self, tmp_path):
        code = "x=1\n"
        r = _check(tmp_path, code)
        for iss in r["issues"]:
            assert "code" in iss
            assert "description" in iss
            assert "severity" in iss
            assert iss["severity"] in ("high", "medium", "low")


# ═══════ Автоисправление ═══════

class TestAutofix:
    def test_fixes_spacing(self, tmp_path):
        result = _fix("x=1\n")
        assert "x = 1" in result["fixed_code"]

    def test_removes_unused_import(self, tmp_path):
        result = _fix("import os\n\nx = 1\n")
        assert "import os" not in result["fixed_code"]
        assert result["changed"] is True

    def test_clean_code_unchanged(self, tmp_path):
        code = "x = 1\n"
        result = _fix(code)
        assert result["changed"] is False

    def test_fixes_multiple_issues(self, tmp_path):
        code = "import os\nimport sys\nx = 1\ny =  2\n"
        result = _fix(code)
        assert "import os" not in result["fixed_code"]
        assert "import sys" not in result["fixed_code"]
        assert result["changed"] is True

    def test_fixed_code_passes_check(self, tmp_path):
        code = "import os\nimport sys\nx=1\ny =  2\n"
        result = _fix(code)
        p = tmp_path / "fixed.py"
        p.write_text(result["fixed_code"], encoding="utf-8")
        r = check_python_code(p, "fixed.py")
        assert r["total_issues"] == 0, f"After autofix still {r['total_issues']} issues"

    def test_preserves_logic(self, tmp_path):
        code = "def add(a , b):\n    return a + b\n"
        result = _fix(code)
        assert "def add(a, b):" in result["fixed_code"]
        assert "return a + b" in result["fixed_code"]


# ═══════ Сложные и пограничные случаи ═══════

class TestEdgeCases:
    def test_unicode_content(self, tmp_path):
        code = '# Привет мир\nx = "Тестовая строка"\nprint(x)\n'
        r = _check(tmp_path, code)
        assert r["file_type"] == "python"

    def test_very_long_file(self, tmp_path):
        lines = [f"x_{i} = {i}" for i in range(200)]
        code = "\n".join(lines) + "\n"
        r = _check(tmp_path, code)
        assert r["total_issues"] >= 0
        assert len(r["source_lines"]) == 200

    def test_only_comments(self, tmp_path):
        code = "# This is a comment\n# Another comment\n"
        r = _check(tmp_path, code)
        assert r["total_issues"] == 0

    def test_docstring_only(self, tmp_path):
        code = '"""Module docstring."""\n'
        r = _check(tmp_path, code)
        assert r["total_issues"] == 0

    def test_syntax_error_still_returns_report(self, tmp_path):
        code = "def f(\n"  # syntax error
        r = _check(tmp_path, code)
        # flake8 reports E999 for syntax errors
        assert r["file_type"] == "python"
        codes = {i["code"] for i in r["issues"]}
        assert "E999" in codes

    def test_deduplication(self, tmp_path):
        """Ошибки на одной строке с одним кодом не должны дублироваться."""
        code = "x=1+2+3+4+5\n"
        r = _check(tmp_path, code)
        e225 = [i for i in r["issues"] if i["code"] == "E225"]
        assert len(e225) <= 1  # deduplicated

    def test_russian_descriptions(self, tmp_path):
        """Описания ошибок должны быть на русском."""
        code = "x=1\n"
        r = _check(tmp_path, code)
        e225 = [i for i in r["issues"] if i["code"] == "E225"]
        if e225:
            assert any(ord(c) > 127 for c in e225[0]["description"]), \
                "Описание должно быть на русском"
