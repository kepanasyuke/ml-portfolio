"""Тесты проекта 6: PSI, KS и алерты мониторинга."""

from fastapi.testclient import TestClient

from projects.ml_monitor import service
from projects.ml_monitor.app import app

client = TestClient(app)


def test_psi_zero_for_identical_distributions():
    values = service.reference().gmv_30d.to_numpy()
    assert service.psi(values, values) < 0.01


def test_psi_grows_with_shift():
    calm = service.report(1.0)["features"]
    shifted = service.report(1.8)["features"]
    calm_max = max(row["psi"] for row in calm)
    shifted_max = max(row["psi"] for row in shifted)
    assert shifted_max > calm_max


def test_shift_raises_alerts():
    assert service.summary(1.8)["flagged"] >= 1


def test_feature_table_covers_all_features():
    rows = service.report(1.2)["features"]
    assert [row["feature"] for row in rows] == list(service.FEATURES)


def test_status_thresholds():
    assert service.status_of(0.05) == "ok"
    assert service.status_of(0.15) == "warn"
    assert service.status_of(0.4) == "bad"


def test_drift_endpoint_returns_scores_block():
    payload = client.get("/api/drift?factor=1.5").json()
    assert {"features", "scores", "alerts", "meta"} <= set(payload)
    assert payload["meta"]["factor"] == 1.5


def test_summary_endpoint_reports_max_psi():
    payload = client.get("/api/summary?factor=1.5").json()
    assert payload["max_psi"] >= 0
    assert payload["current"] > 0
