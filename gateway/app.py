"""Единый шлюз: кабинет компании на корне и семь проектов под /p/<slug>/.

Один процесс, один порт: разделы сохраняют свои API, но живут в общем кабинете
со сквозной навигацией. Ссылки и ассеты строятся от root_path, поэтому
приложение одинаково работает и в шлюзе, и отдельным сервисом.
"""

from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

from gateway import service
from projects.ab_lab.app import app as ab_app
from projects.churn_clv.app import app as churn_app
from projects.ml_monitor.app import app as monitor_app
from projects.ml_pipeline.app import app as pipeline_app
from projects.promo_optimizer.app import app as promo_app
from projects.sql_lab.app import app as sql_app
from projects.uplift_engine.app import app as uplift_app
from shared import web

PORT = 8000
PROJECT_DIR = Path(__file__).resolve().parent
MOUNTS = {
    "uplift-engine": uplift_app,
    "promo-optimizer": promo_app,
    "ab-lab": ab_app,
    "ml-pipeline": pipeline_app,
    "churn-clv": churn_app,
    "ml-monitor": monitor_app,
    "sql-lab": sql_app,
}


def cabinet(request: Request) -> HTMLResponse:
    """Страница кабинета со сводкой по компании."""
    return web.page(request, "cabinet.html", {**service.PAGE, "portal": True})


def mount_projects(app: FastAPI) -> FastAPI:
    """Подключает разделы под общим префиксом /p."""
    [app.mount(f"/p/{slug}", project) for slug, project in MOUNTS.items()]
    return app


def build() -> FastAPI:
    """Шлюз с кабинетом, общими стилями и подключёнными разделами."""
    app = web.mount_health(web.make_app("ML-кабинет", PROJECT_DIR, cabinet), "gateway")
    return mount_projects(app)


app = build()


@app.get("/api/overview")
def overview(refresh: bool = False) -> dict[str, object]:
    """Сводка кабинета по всем разделам."""
    return service.fresh(refresh)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=PORT)
