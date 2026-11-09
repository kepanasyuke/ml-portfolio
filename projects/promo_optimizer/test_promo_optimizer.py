"""Тесты проекта 2: ограничения оптимизатора и отчёт для API."""

from fastapi.testclient import TestClient

from projects.promo_optimizer import service
from projects.promo_optimizer.app import app

client = TestClient(app)


def test_select_respects_budget():
    plan = service.select(service.candidate_frame(), budget=20_000.0, cpo_cap=500.0)
    assert plan.exp_spend.sum() <= 20_000.0
    assert plan.user_id.is_unique


def test_select_respects_cpo_cap():
    plan = service.select(service.candidate_frame(), budget=200_000.0, cpo_cap=150.0)
    cpo = plan.exp_spend.sum() / max(plan.tau.sum(), 1e-9)
    assert cpo <= 150.0 + 1e-6


def test_optimizer_beats_blanket_on_roi():
    result = service.optimize()
    assert result["plan"]["roi"] >= result["blanket"]["roi"]


def test_optimize_endpoint_returns_three_scenarios():
    response = client.post("/api/optimize", json={"budget": 150_000, "cpo_cap": 250})
    payload = response.json()
    assert response.status_code == 200
    assert {"plan", "blanket", "by_promo", "top"} <= set(payload)
    assert payload["plan"]["users"] > 0


def test_limits_endpoint_reports_pool():
    limits = client.get("/api/limits").json()
    assert limits["candidates"] == limits["users"] * 4


def test_health_endpoint():
    assert client.get("/api/health").json()["service"] == "promo-optimizer"
