"""Скрипт для замера точности и полноты сервиса на реальных работах.

Зачем нужно:
    SMART-цель проекта — точность не менее 85%. Эту цифру нужно реально
    посчитать на выборке студенческих работ, иначе на защите она ничем не
    подкреплена.

Как пользоваться:
    1. Создайте папку benchmark/files и положите туда все файлы для проверки
       (.py и/или .docx).
    2. Создайте файл benchmark/ground_truth.json с разметкой — какие ошибки
       реально есть в каждом файле. Формат описан ниже.
    3. Запустите: python benchmark/run_benchmark.py
    4. Получите итоговый отчёт с precision/recall/F1 в консоли и
       benchmark/results.json со всеми деталями.

Формат ground_truth.json:
    {
        "файл1.py": {
            "true_issues": [
                {"line": 5, "code": "E225"},
                {"line": 12, "code": "F401"}
            ]
        },
        "документ1.docx": {
            "true_issues": [
                {"code": "FONT_MISMATCH"},
                {"code": "MARGIN_MISMATCH"}
            ]
        }
    }

Метрики (в академическом смысле):
    precision (точность) = TP / (TP + FP)
        Из всего, что нашёл сервис, какая доля — настоящие ошибки.
        Высокая точность = сервис не «шумит».
    recall (полнота) = TP / (TP + FN)
        Из всех настоящих ошибок какую долю сервис нашёл.
        Высокая полнота = сервис не пропускает.
    F1 = гармоническое среднее точности и полноты.
        Сводная метрика: одинаково плохо, если страдает либо одно, либо другое.

    TP — true positive  — нашёл и она реально есть
    FP — false positive — нашёл, но это не ошибка (ложная тревога)
    FN — false negative — не нашёл, но ошибка есть (пропуск)

Что считать «совпадением»:
    Для Python — совпадает строка И код.
    Для .docx — совпадает только код (точное место сложно соотносить).
    Эту логику можно ужесточить, но для учебного проекта такой меры хватает.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Добавляем корень проекта в sys.path, чтобы импорты работали
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.checkers.code_checker import check_python_code  # noqa: E402
from app.checkers.docx_checker import check_docx_document  # noqa: E402

BENCHMARK_DIR = ROOT / "benchmark"
FILES_DIR = BENCHMARK_DIR / "files"
GROUND_TRUTH = BENCHMARK_DIR / "ground_truth.json"
RESULTS = BENCHMARK_DIR / "results.json"


def _python_match(predicted: dict, expected: dict) -> bool:
    """Совпадение для Python: одна строка и один код."""
    return predicted["line"] == expected["line"] and predicted["code"] == expected["code"]


def _docx_match(predicted: dict, expected: dict) -> bool:
    """Совпадение для .docx: только код (без привязки к месту)."""
    return predicted["code"] == expected["code"]


def evaluate_file(file_path: Path, true_issues: list[dict]) -> dict:
    """Запускает чекер на одном файле и сравнивает с эталоном."""
    extension = file_path.suffix.lower()
    if extension == ".py":
        report = check_python_code(file_path, file_path.name)
        match_fn = _python_match
    elif extension == ".docx":
        report = check_docx_document(file_path, file_path.name)
        match_fn = _docx_match
    else:
        return {"skipped": True, "reason": f"Неподдерживаемое расширение: {extension}"}

    predicted = report["issues"]

    # TP: для каждого предсказания ищем совпадение в эталоне
    matched_true_indexes: set[int] = set()
    tp = 0
    fp = 0
    for pred in predicted:
        found = False
        for j, true_issue in enumerate(true_issues):
            if j in matched_true_indexes:
                continue
            if match_fn(pred, true_issue):
                matched_true_indexes.add(j)
                tp += 1
                found = True
                break
        if not found:
            fp += 1

    # FN: эталонные ошибки, которые не были «закрыты» предсказаниями
    fn = len(true_issues) - len(matched_true_indexes)

    return {
        "file": file_path.name,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "predicted_total": len(predicted),
        "true_total": len(true_issues),
    }


def calc_metrics(tp: int, fp: int, fn: int) -> dict:
    """Считает precision, recall, F1 из накопленных счётчиков."""
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall) > 0 else 0.0
    )
    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
    }


def main() -> int:
    if not GROUND_TRUTH.exists():
        print(f"❌ Не найден файл эталонной разметки: {GROUND_TRUTH}")
        print("   Создайте его по образцу из docstring этого скрипта.")
        return 1
    if not FILES_DIR.exists():
        print(f"❌ Не найдена папка с файлами: {FILES_DIR}")
        return 1

    with open(GROUND_TRUTH, encoding="utf-8") as f:
        ground_truth = json.load(f)

    file_results = []
    total_tp = total_fp = total_fn = 0

    for filename, data in ground_truth.items():
        file_path = FILES_DIR / filename
        if not file_path.exists():
            print(f"⚠️  Файл не найден, пропускаем: {filename}")
            continue
        result = evaluate_file(file_path, data.get("true_issues", []))
        if result.get("skipped"):
            print(f"⚠️  {filename}: {result['reason']}")
            continue
        file_results.append(result)
        total_tp += result["tp"]
        total_fp += result["fp"]
        total_fn += result["fn"]
        print(
            f"  {filename}: TP={result['tp']} FP={result['fp']} FN={result['fn']} "
            f"(нашлось {result['predicted_total']}, в эталоне {result['true_total']})"
        )

    if not file_results:
        print("❌ Не удалось обработать ни одного файла.")
        return 1

    overall = calc_metrics(total_tp, total_fp, total_fn)

    print()
    print("=" * 60)
    print("ИТОГИ")
    print("=" * 60)
    print(f"Файлов обработано: {len(file_results)}")
    print(f"True Positive  (правильно нашёл):    {total_tp}")
    print(f"False Positive (ложная тревога):     {total_fp}")
    print(f"False Negative (пропустил ошибку):   {total_fn}")
    print()
    print(f"Точность (precision): {overall['precision']:.2%}")
    print(f"Полнота  (recall):    {overall['recall']:.2%}")
    print(f"F1-мера:              {overall['f1']:.2%}")
    print()
    threshold = 0.85
    if overall["precision"] >= threshold:
        print(f"✓ Точность ≥ {threshold:.0%} — SMART-цель достигнута")
    else:
        print(f"✗ Точность < {threshold:.0%} — нужно улучшать чекер")

    # Сохраняем подробный результат
    RESULTS.write_text(
        json.dumps(
            {
                "overall": overall,
                "totals": {"tp": total_tp, "fp": total_fp, "fn": total_fn},
                "files": file_results,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nПодробности сохранены в {RESULTS}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
