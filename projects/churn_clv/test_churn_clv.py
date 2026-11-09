"""Тесты проекта 5: RFM, удержание и CLV."""

from fastapi.testclient import TestClient

from projects.churn_clv import service
from projects.churn_clv.app import app

client = TestClient(app)


def test_segments_cover_all_customers():
    frame = service.table()
    assert frame.segment.notna().all()
    assert set(frame.segment.unique()) <= set(service.SEGMENT_NAMES) | {"Новички"}


def test_retention_is_probability():
    frame = service.table()
    assert frame.retention.between(0, 1).all()


def test_clv_positive_and_varies():
    frame = service.table()
    assert (frame.clv >= 0).all()
    assert frame.clv.sum() > 0
    assert frame.clv.std() > 0


def test_churn_model_ranks_risk():
    frame = service.scored_frame(service.make_base(1200, seed=3))
    active = frame[frame.days_since_order < 15].retention.mean()
    sleeping = frame[frame.days_since_order > 70].retention.mean()
    assert active > sleeping


def test_summary_contains_at_risk_value():
    summary = service.summary()
    assert summary["total_clv"] > summary["at_risk_clv"] >= 0


def test_segments_endpoint_sorted_by_value():
    rows = client.get("/api/segments").json()
    totals = [row["total_clv"] for row in rows]
    assert totals == sorted(totals, reverse=True)


def test_customers_endpoint_returns_limit():
    assert len(client.get("/api/customers?limit=5").json()) == 5
