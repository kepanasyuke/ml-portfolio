"""HTTP-слой проекта 2: форма ограничений и расчёт плана распределения промокодов."""

from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from projects.promo_optimizer import service
from shared import web

PROJECT_DIR = Path(__file__).resolve().parent
PORT = 8002


class OptimizeRequest(BaseModel):
    """Ограничения бизнеса, которые вводит менеджер кампании."""

    budget: float = Field(default=90_000.0, ge=1_000.0, le=5_000_000.0)
    cpo_cap: float = Field(default=220.0, ge=10.0, le=5_000.0)


def index(request: Request) -> HTMLResponse:
    """Дашборд оптимизатора промокодов."""
    return web.page(request, "promo_optimizer.html", {**service.PAGE, "port": PORT})


def build() -> FastAPI:
    """Приложение проекта с общими стилями и health-check."""
    return web.mount_health(web.make_app("Promo Optimizer", PROJECT_DIR, index), "promo-optimizer")


app = build()


@app.get("/api/limits")
def limits() -> dict[str, float]:
    """Ограничения по умолчанию и размер пула кандидатов."""
    return service.limits()


@app.post("/api/optimize")
def optimize(payload: OptimizeRequest) -> dict[str, object]:
    """План распределения под введённые бюджет и CPO."""
    return service.optimize(payload.budget, payload.cpo_cap)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=PORT)
