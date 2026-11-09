"""HTTP-слой проекта 5: сегменты, отток и клиентская ценность."""

from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

from projects.churn_clv import service
from shared import web

PROJECT_DIR = Path(__file__).resolve().parent
PORT = 8005


def index(request: Request) -> HTMLResponse:
    """Дашборд клиентской ценности."""
    return web.page(request, "churn_clv.html", {**service.PAGE, "port": PORT})


def build() -> FastAPI:
    """Приложение проекта с общими стилями и health-check."""
    return web.mount_health(web.make_app("Churn & CLV", PROJECT_DIR, index), "churn-clv")


app = build()


@app.get("/api/summary")
def summary() -> dict[str, float]:
    """Ключевые цифры базы: CLV, отток, удержание."""
    return service.summary()


@app.get("/api/segments")
def segments() -> list[dict]:
    """Агрегаты по RFM-сегментам."""
    return service.segments_table()


@app.get("/api/customers")
def customers(limit: int = 12) -> list[dict]:
    """Топ клиентов по CLV."""
    return service.top_customers(limit)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=PORT)
