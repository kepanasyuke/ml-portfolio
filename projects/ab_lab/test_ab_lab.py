"""Тесты проекта 3: дизайн, CUPED и API A/B-лаборатории."""

from fastapi.testclient import TestClient

from projects.ab_lab import service
from projects.ab_lab.app import app

client = TestClient(app)


def test_sample_size_grows_with_smaller_effect():
    coarse = service.sample_size(1800.0, 700.0, 0.10)
    fine = service.sample_size(1800.0, 700.0, 0.02)
    assert fine > coarse > 0


def test_duration_is_positive():
    assert service.design()["days"] >= 1


def test_cuped_reduces_variance():
    control, test = service.split(service.data())
    assert service.variance_reduction(control, test, service.pooled_theta(control, test)) > 0


def test_cuped_keeps_effect_close_to_naive():
    report = service.report(service.data())
    assert (
        abs(report["cuped"]["diff"] - report["naive"]["diff"]) < abs(report["naive"]["diff"]) * 0.5
    )


def test_sequential_p_value_is_probability():
    report = service.report(service.data())
    assert 0.0 <= report["naive"]["sequential_p"] <= 1.0


def test_design_endpoint_accepts_mde():
    payload = client.get("/api/design?mde=0.05&traffic=2000").json()
    assert payload["mde_rel"] == 0.05
    assert payload["days"] <= payload["total"]


def test_result_endpoint_has_three_views():
    payload = client.get("/api/result").json()
    assert {"naive", "cuped", "reduction", "counts"} <= set(payload)
