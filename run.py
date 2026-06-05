"""Точка входа для запуска SmartDoc & Code Review.

Запуск:
    python run.py

После запуска откройте http://127.0.0.1:8000 в браузере.
"""
import os
import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=os.environ.get("ENV") != "production",
        log_level="info",
    )
