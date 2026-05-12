# SmartDoc & Code Review v6

Веб-платформа для автоматической проверки Python-кода (PEP 8) и документов .docx (нормоконтроль ГОСТ/АГУ).

## Возможности

- Проверка .py на соответствие PEP 8 через flake8 (русские описания ошибок, дедупликация)
- Нормоконтроль .docx: шрифт, кегль, интервал, отступ, поля, подписи к рисункам/таблицам, список литературы
- Автоисправление .py (autoflake + autopep8, 3 прохода) и .docx (поля, шрифт, кегль, интервал, отступ, цвет, картинки)
- Пользовательские правила проверки .docx — пресет АГУ (ГОСТ) или свои значения (шрифт, кегль, поля, интервал)
- Подсветка ошибок прямо в исходном коде с minimap, тултипами и навигацией
- Вставка кода из буфера обмена (Ctrl+V) без создания файла
- Экспорт отчёта в PDF с фрагментами кода рядом с каждой ошибкой
- История проверок в браузере (localStorage, до 30 записей)
- Светлая / тёмная тема, drag-n-drop, анимации, адаптивный дизайн

## Быстрый старт

```bash
pip install -r requirements.txt
python run.py
```

Откройте http://127.0.0.1:8000

## Деплой на Render.com

1. Загрузите проект на GitHub (создайте репозиторий и запушьте код)
2. Откройте [render.com](https://render.com) и зарегистрируйтесь
3. Нажмите **New → Web Service**
4. Подключите GitHub-репозиторий с проектом
5. Render автоматически определит настройки из `render.yaml`
6. Нажмите **Create Web Service**
7. Через 2–3 минуты сервис будет доступен по ссылке вида `https://smartdoc-xxxx.onrender.com`

Бесплатный тариф Render: сервис засыпает после 15 минут простоя. Первый запрос после сна может занять до 30 секунд.

## Тесты

```bash
pip install pytest
pytest tests/ -v
```

## Структура

```
smartdoc_v6/
├── app/
│   ├── main.py                    # FastAPI: все маршруты
│   ├── pdf_export.py              # генерация PDF (reportlab)
│   ├── checkers/
│   │   ├── code_checker.py        # Python / flake8 + русские описания
│   │   ├── code_fixer.py          # autoflake + autopep8 (3 прохода)
│   │   ├── docx_checker.py        # нормоконтроль ГОСТ + пресеты правил
│   │   ├── docx_extras.py         # подписи, библиография
│   │   └── docx_fixer.py          # автоисправление .docx
│   ├── templates/index.html
│   └── static/{style.css, app.js}
├── tests/                         # 40+ тестов (pytest)
├── benchmark/                     # замер точности
├── sample_files/                  # демо-файлы
├── requirements.txt
└── run.py
```

## API

| Метод | Путь | Что делает |
|---|---|---|
| POST | `/api/check` | Проверка (.py / .docx) → JSON-отчёт |
| POST | `/api/autofix` | Автоисправление → скачивание файла |
| POST | `/api/export-pdf` | Отчёт → PDF-файл |
| GET  | `/api/presets` | Список пресетов правил для .docx |
| GET  | `/health` | Health-check |

Эндпоинты `/api/check` и `/api/autofix` принимают необязательное поле `docx_rules` (JSON) для пользовательских правил проверки .docx.

## Деплой на Render.com

1. Загрузите проект на GitHub
2. На [render.com](https://render.com) создайте **New Web Service**
3. Подключите репозиторий
4. Настройки:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Python Version**: 3.12
5. Нажмите **Create Web Service** — через 2–3 минуты сайт будет доступен по публичной ссылке

Или используйте файл `render.yaml` — Render подхватит настройки автоматически.

## Автор

Данил Полстянов — poncikovdanila@gmail.com
АГУ им. В. Н. Татищева, направление 09.03.02, 2026
