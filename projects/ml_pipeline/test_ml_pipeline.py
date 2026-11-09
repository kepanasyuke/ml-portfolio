"""Тесты проекта 4: кэш стадий, манифест и артефакты локального S3."""

import shutil

from fastapi.testclient import TestClient

from projects.ml_pipeline import service
from projects.ml_pipeline.app import app

client = TestClient(app)


def clean_bucket():
    shutil.rmtree(service.BUCKET, ignore_errors=True)


def test_first_run_executes_all_stages():
    clean_bucket()
    result = service.run(force=True)
    assert [stage["name"] for stage in result["stages"]] == list(service.STAGES)
    assert all(stage["status"] == "ran" for stage in result["stages"])


def test_second_run_uses_cache():
    clean_bucket()
    service.run(force=True)
    second = service.run()
    assert all(stage["status"] == "cached" for stage in second["stages"])


def test_force_recomputes_everything():
    clean_bucket()
    service.run(force=True)
    forced = service.run(force=True)
    assert all(stage["status"] == "ran" for stage in forced["stages"])


def test_manifest_records_hashes():
    clean_bucket()
    service.run(force=True)
    saved = service.manifest()
    assert set(saved["hashes"]) == set(service.STAGES)


def test_artifacts_include_model_and_metrics():
    clean_bucket()
    service.run(force=True)
    keys = {item["key"] for item in service.artifacts()}
    assert {service.DATA_KEY, service.MODEL_KEY, service.METRICS_KEY} <= keys


def test_evaluate_metrics_are_positive():
    clean_bucket()
    result = service.run(force=True)
    assert result["metrics"]["auuc"] > 0


def test_run_endpoint_returns_stages():
    payload = client.post("/api/run", json={"force": True}).json()
    assert payload["bucket"]
    assert len(payload["stages"]) == len(service.STAGES)
