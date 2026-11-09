"""HTTP-слой проекта 7: редактор SQL и выполнение запросов по витрине заказов."""

from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from projects.sql_lab import service
from shared import web

PROJECT_DIR = Path(__file__).resolve().parent
PORT = 8007


class QueryRequest(BaseModel):
    """Текст SQL-запроса из редактора."""

    sql: str = Field(min_length=6, max_length=4000)


def index(request: Request) -> HTMLResponse:
    """Дашборд SQL-лаборатории."""
    return web.page(request, "sql_lab.html", {**service.PAGE, "port": PORT})


def build() -> FastAPI:
    """Приложение проекта с общими стилями и health-check."""
    return web.mount_health(web.make_app("SQL Metrics Lab", PROJECT_DIR, index), "sql-lab")


app = build()


@app.get("/api/queries")
def queries() -> dict[str, object]:
    """Готовые запросы и схема витрины."""
    return {"presets": service.presets(), "schema": service.schema()}


@app.post("/api/query")
def query(payload: QueryRequest) -> dict[str, object]:
    """Выполняет read-only запрос и возвращает таблицу результата."""
    return service.run_query(payload.sql)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=PORT)
