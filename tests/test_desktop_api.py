"""Тесты моста оконного приложения: команды окна без запуска GUI."""

import webbrowser
from types import SimpleNamespace

from desktop.api import DesktopApi
from desktop.app import parse_args


def make_api():
    calls = []
    window = SimpleNamespace(
        toggle_fullscreen=lambda: calls.append("fullscreen"),
        destroy=lambda: calls.append("destroy"),
        set_title=calls.append,
    )
    return DesktopApi().set_window(window), calls


def test_set_window_returns_bridge():
    api, _ = make_api()
    assert api.window is not None


def test_toggle_fullscreen_calls_window():
    api, calls = make_api()
    assert api.toggle_fullscreen() is True
    assert calls == ["fullscreen"]


def test_set_title_updates_window():
    api, calls = make_api()
    api.set_title("ML-кабинет")
    assert calls == ["ML-кабинет"]


def test_close_destroys_window():
    api, calls = make_api()
    assert api.close() is True
    assert calls == ["destroy"]


def test_open_browser_uses_system_browser(monkeypatch):
    opened = []
    monkeypatch.setattr(webbrowser, "open", opened.append)
    api, _ = make_api()
    api.open_browser("http://127.0.0.1:8765/")
    assert opened == ["http://127.0.0.1:8765/"]


def test_about_reports_sections():
    api, _ = make_api()
    info = api.about()
    assert info["sections"] == 7
    assert "FastAPI" in info["stack"]


def test_parse_args_defaults_to_webview():
    args = parse_args([])
    assert args.mode == "webview"
    assert args.port == 8765


def test_parse_args_accepts_app_mode():
    args = parse_args(["--mode", "app", "--port", "9000"])
    assert args.mode == "app"
    assert args.port == 9000
