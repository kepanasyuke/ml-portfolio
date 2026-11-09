"""HTTP-слой проекта 4: запуск пайплайна и состояние локального S3."""

from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from projects.ml_pipeline import service
from shared import web

PROJECT_DIR = Path(__file__).resolve().parent
PORT = 8004


class RunRequest(BaseModel):
    """Флаг пересчёта: force игнорирует кэш стадий."""

    force: bool = False


def index(request: Request) -> HTMLResponse:
    """Дашборд пайплайна."""
    return web.page(request, "ml_pipeline.html", {**service.PAGE, "port": PORT})


def build() -> FastAPI:
    """Приложение проекта с общими стилями и health-check."""
    return web.mount_health(web.make_app("ML Pipeline", PROJECT_DIR, index), "ml-pipeline")


app = build()


@app.get("/api/state")
def state() -> dict[str, object]:
    """Последний манифест и объекты бакета."""
    return service.state()


@app.post("/api/run")
def run(payload: RunRequest) -> dict[str, object]:
    """Прогон пайплайна с учётом кэша стадий."""
    return service.run(payload.force)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=PORT)
