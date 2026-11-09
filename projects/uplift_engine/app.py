"""HTTP-слой проекта 1: страница дашборда и JSON-ручки uplift-модели."""

from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

from projects.uplift_engine import service
from shared import web

PROJECT_DIR = Path(__file__).resolve().parent
PORT = 8001


def index(request: Request) -> HTMLResponse:
    """Дашборд проекта в фирменном каркасе портфолио."""
    return web.page(request, "uplift_engine.html", {**service.PAGE, "port": PORT})


def build() -> FastAPI:
    """Приложение с общими стилями, health-check и страницей дашборда."""
    return web.mount_health(web.make_app("Uplift Engine", PROJECT_DIR, index), "uplift-engine")


app = build()


@app.get("/api/summary")
def summary() -> dict[str, object]:
    """Размеры выборок, метрики и модель-чемпион."""
    return service.summary()


@app.get("/api/qini")
def qini() -> dict[str, object]:
    """Кривые Qini обеих моделей."""
    return service.qini()


@app.get("/api/segments")
def segments() -> list[dict]:
    """Uplift и ожидаемая маржа по сегментам."""
    return service.segment_view()


@app.get("/api/recommendations")
def recommendations(limit: int = 12) -> list[dict]:
    """Топ пользователей под промокод."""
    return service.top_users(limit)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=PORT)
