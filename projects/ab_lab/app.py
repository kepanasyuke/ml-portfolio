"""HTTP-слой проекта 3: калькулятор дизайна теста и разбор эксперимента."""

from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

from projects.ab_lab import service
from shared import web

PROJECT_DIR = Path(__file__).resolve().parent
PORT = 8003


def index(request: Request) -> HTMLResponse:
    """Дашборд A/B-лаборатории."""
    return web.page(request, "ab_lab.html", {**service.PAGE, "port": PORT})


def build() -> FastAPI:
    """Приложение проекта с общими стилями и health-check."""
    return web.mount_health(web.make_app("A/B Lab", PROJECT_DIR, index), "ab-lab")


app = build()


@app.get("/api/design")
def design(mde: float = service.MDE, traffic: int = service.TRAFFIC) -> dict[str, float]:
    """Размер выборки и срок теста для заданного MDE и трафика."""
    return service.design(mde, traffic)


@app.get("/api/result")
def result() -> dict[str, object]:
    """Эффект в эксперименте: наивная и CUPED-оценки."""
    return service.report(service.data())


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=PORT)
