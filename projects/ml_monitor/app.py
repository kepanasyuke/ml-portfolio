"""HTTP-слой проекта 6: отчёт по дрейфу и сводка алертов."""

from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

from projects.ml_monitor import service
from shared import web

PROJECT_DIR = Path(__file__).resolve().parent
PORT = 8006


def index(request: Request) -> HTMLResponse:
    """Дашборд мониторинга дрейфа."""
    return web.page(request, "ml_monitor.html", {**service.PAGE, "port": PORT})


def build() -> FastAPI:
    """Приложение проекта с общими стилями и health-check."""
    return web.mount_health(web.make_app("ML Monitor", PROJECT_DIR, index), "ml-monitor")


app = build()


@app.get("/api/drift")
def drift(factor: float = 1.0) -> dict[str, object]:
    """Таблица дрейфа признаков при заданном сдвиге спроса."""
    return service.report(factor)


@app.get("/api/summary")
def summary(factor: float = 1.0) -> dict[str, float]:
    """KPI мониторинга: максимальный PSI и число алертов."""
    return service.summary(factor)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=PORT)
