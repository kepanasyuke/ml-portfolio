"""Общий веб-слой: FastAPI-приложение, монтирование стилей и шаблонов.

Каждый проект импортирует make_app/page, поэтому верстка, палитра и навигация
не копируются семь раз, а живут в одном месте.
"""

from functools import partial
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

HERE = Path(__file__).resolve().parent
ASSETS = HERE / "assets"
TEMPLATES = Jinja2Templates(directory=str(HERE / "templates"))

PROJECTS = (
    {"slug": "uplift-engine", "title": "Uplift Engine", "port": 8001, "icon": "uplift"},
    {"slug": "promo-optimizer", "title": "Promo Optimizer", "port": 8002, "icon": "promo"},
    {"slug": "ab-lab", "title": "A/B Lab", "port": 8003, "icon": "ab"},
    {"slug": "ml-pipeline", "title": "ML Pipeline", "port": 8004, "icon": "pipeline"},
    {"slug": "churn-clv", "title": "Churn & CLV", "port": 8005, "icon": "clv"},
    {"slug": "ml-monitor", "title": "ML Monitor", "port": 8006, "icon": "monitor"},
    {"slug": "sql-lab", "title": "SQL Metrics Lab", "port": 8007, "icon": "sql"},
)


def create_app(title: str) -> FastAPI:
    """Пустое приложение с открытым OpenAPI для портфолио."""
    return FastAPI(
        title=title, version="0.1.0", docs_url="/api/docs", openapi_url="/api/openapi.json"
    )


def mount_project_static(app: FastAPI, project_dir: str | Path) -> FastAPI:
    """Монтирует стили конкретного проекта по адресу /assets."""
    app.mount("/assets", StaticFiles(directory=str(Path(project_dir) / "static")), name="assets")
    return app


def with_static(app: FastAPI, project_dir: str | Path) -> FastAPI:
    """Добавляет общие стили портфолио к приложению проекта."""
    app.mount("/static", StaticFiles(directory=str(ASSETS)), name="static")
    return mount_project_static(app, project_dir)


def with_index(app: FastAPI, index) -> FastAPI:
    """Регистрирует HTML-страницу проекта по корню."""
    app.add_api_route("/", index, methods=["GET"], response_class=HTMLResponse)
    return app


def make_app(title: str, project_dir: str | Path, index) -> FastAPI:
    """Собирает FastAPI-приложение со стилями, статикой и страницей проекта."""
    return with_index(with_static(create_app(title), project_dir), index)


def nav_links(root: str, portal: bool = False) -> list[dict]:
    """Ссылки между проектами: внутри шлюза относительные, отдельно — по портам."""
    base = root.rsplit("/", 1)[0] if root else ""
    return [
        {
            **item,
            "href": f"{base}/{item['slug']}/"
            if base
            else (f"/p/{item['slug']}/" if portal else f"http://127.0.0.1:{item['port']}/"),
        }
        for item in PROJECTS
    ]


def render_page(request: Request, template: str, root: str, context: dict) -> HTMLResponse:
    """Рендерит шаблон, подставляя префикс и ссылки навигации."""
    portal = bool(context.pop("portal", False))
    return TEMPLATES.TemplateResponse(
        request, template, {**context, "projects": nav_links(root, portal), "root": root}
    )


def page(request: Request, template: str, context: dict) -> HTMLResponse:
    """Рендерит страницу в общем каркасе с учётом префикса шлюза."""
    root = request.scope.get("root_path", "").rstrip("/")
    return render_page(request, template, root, context)


def health(app_name: str) -> dict[str, str]:
    """Единый health-check для всех сервисов."""
    return {"status": "ok", "service": app_name}


def mount_health(app: FastAPI, app_name: str) -> FastAPI:
    """Регистрирует /api/health в приложении проекта."""
    app.add_api_route("/api/health", partial(health, app_name), methods=["GET"])
    return app
