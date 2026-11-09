"""Тесты шлюза: кабинет, монтирование разделов и сквозные ссылки."""

from fastapi.testclient import TestClient

from gateway.app import app

client = TestClient(app)


def test_cabinet_renders_on_root():
    page = client.get("/")
    assert page.status_code == 200
    assert "ML-кабинет" in page.text
    assert 'id="cards"' in page.text


def test_overview_returns_all_sections():
    payload = client.get("/api/overview").json()
    slugs = {card["slug"] for card in payload["cards"]}
    assert payload["sections"] == 7
    assert "uplift-engine" in slugs
    assert "sql-lab" in slugs


def test_overview_cards_have_values_and_links():
    payload = client.get("/api/overview").json()
    for card in payload["cards"]:
        assert card["value"]
        assert card["href"] == f"/p/{card['slug']}/"
        assert card["status"] in {"ok", "warn", "bad"}


def test_mounted_project_page_uses_gateway_links():
    page = client.get("/p/uplift-engine/")
    assert page.status_code == 200
    assert "/p/promo-optimizer/" in page.text


def test_mounted_project_page_keeps_assets_under_prefix():
    page = client.get("/p/ab-lab/")
    assert "/p/ab-lab/static/tokens.css" in page.text
    assert "/p/ab-lab/assets/app.js" in page.text


def test_mounted_api_responds():
    response = client.get("/p/ml-monitor/api/summary?factor=1.2")
    assert response.status_code == 200
    assert response.json()["max_psi"] >= 0


def test_mounted_health_endpoint():
    assert client.get("/p/sql-lab/api/health").json()["service"] == "sql-lab"


def test_gateway_health_endpoint():
    assert client.get("/api/health").json()["service"] == "gateway"


def test_nav_uses_svg_icons_for_every_section():
    page = client.get("/p/uplift-engine/").text
    icons = ("uplift", "promo", "ab", "pipeline", "clv", "monitor", "sql")
    assert all(f"#i-{icon}" in page for icon in icons)
    assert "#i-logo" in page
    assert "#i-cabinet" in page


def test_desktop_bridge_script_is_loaded():
    page = client.get("/p/ab-lab/").text
    assert "/p/ab-lab/static/desktop.js" in page


def test_cabinet_has_icons_and_brand_mark():
    page = client.get("/").text
    assert 'href="#i-logo"' in page
    assert 'class="brand-mark"' in page


def test_cabinet_shows_store_categories():
    page = client.get("/").text
    assert "/static/img/cat-milk.png" in page
    assert 'class="showcase"' in page


def test_cabinet_shows_product_cards():
    page = client.get("/").text
    assert 'class="products"' in page
    assert page.count('class="product"') == 6
    assert 'class="product-tag"' in page
    assert "89 ₽" in page
