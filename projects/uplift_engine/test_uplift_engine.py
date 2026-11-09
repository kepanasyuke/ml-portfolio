"""Тесты проекта 1: качество uplift-модели и API дашборда."""

from fastapi.testclient import TestClient

from projects.uplift_engine import service
from projects.uplift_engine.app import app

client = TestClient(app)


def test_bundle_trains_on_two_models():
    data = service.bundle()
    assert {"two_model", "transformed"} <= set(data["metrics"])
    assert data["holdout_size"] > 500


def test_two_model_beats_random_ranking():
    metrics = service.bundle()["metrics"]["two_model"]
    assert metrics["auuc"] > 0
    assert metrics["uplift_at_10"] > 0


def test_qini_curve_starts_near_zero_and_grows():
    curve = service.qini()["two_model"]
    assert len(curve["share"]) == len(curve["qini"])
    assert curve["qini"][-1] > curve["qini"][0]


def test_recommendations_sorted_by_expected_margin():
    rows = service.top_users(8)
    margins = [row["expected_margin"] for row in rows]
    assert len(rows) == 8
    assert margins == sorted(margins, reverse=True)


def test_summary_endpoint_reports_champion():
    response = client.get("/api/summary")
    assert response.status_code == 200
    assert response.json()["champion"] in {"two_model", "transformed"}


def test_health_endpoint():
    assert client.get("/api/health").json()["status"] == "ok"


def test_dashboard_renders_metrics_placeholders():
    page = client.get("/").text
    assert "Uplift Engine" in page
    assert 'id="qini-chart"' in page
