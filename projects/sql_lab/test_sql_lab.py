"""Тесты проекта 7: защита от записи, шим диалекта и бизнес-запросы."""

from fastapi.testclient import TestClient

from projects.sql_lab import service
from projects.sql_lab.app import app

client = TestClient(app)


def test_guard_rejects_write_statements():
    assert not service.guard("DELETE FROM orders")["ok"]
    assert not service.guard("SELECT 1; DROP TABLE orders")["ok"]
    assert service.guard("select city from orders -- комментарий")["ok"]


def test_translate_rewrites_trino_functions():
    sql = service.translate(
        "SELECT date_trunc('week', order_date), approx_distinct(user_id) FROM orders"
    )
    assert "strftime('%Y-%W'" in sql
    assert "count(distinct user_id)" in sql


def test_city_query_returns_rows():
    result = service.run_query(service.PRESETS[0]["sql"])
    assert result["count"] >= 3
    assert result["columns"][0] == "city"


def test_all_presets_execute():
    results = [service.run_query(preset["sql"]) for preset in service.presets()]
    assert all(result["count"] > 0 for result in results)


def test_write_endpoint_returns_error_payload():
    payload = client.post("/api/query", json={"sql": "DROP TABLE orders"}).json()
    assert payload["error"]
    assert payload["rows"] == []


def test_query_endpoint_returns_columns():
    payload = client.post(
        "/api/query", json={"sql": "SELECT count(*) AS orders FROM orders"}
    ).json()
    assert payload["columns"] == ["orders"]
    assert payload["rows"][0][0] > 0


def test_schema_lists_order_columns():
    names = [row["name"] for row in service.schema()]
    assert {"order_date", "gmv", "promo_cost"} <= set(names)
