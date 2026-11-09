"""Оконное приложение: шлюз в фоне и отдельное окно с ML-кабинетом.

Два режима запуска:

    python -m desktop.app                  # нативное окно WebView2 (pywebview)
    python -m desktop.app --mode app       # окно браузера без адресной строки (--app)

Оба режима поднимают тот же FastAPI-шлюз на 127.0.0.1:8765, что и в браузере.
"""

import argparse
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

import uvicorn

try:
    import webview
except ImportError:  # pragma: no cover - зависит от окружения
    webview = None

from desktop.api import DesktopApi
from gateway.app import app as gateway_app

PORT = 8765
URL = f"http://127.0.0.1:{PORT}/"
TITLE = "Магнит доставка · ML-кабинет"
BROWSERS = (
    Path("C:/Program Files/Google/Chrome/Application/chrome.exe"),
    Path("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"),
)


def browser_path() -> Path | None:
    """Путь к установленному Chromium-браузеру для режима app."""
    return next((path for path in BROWSERS if path.exists()), None)


def serve(server: uvicorn.Server) -> uvicorn.Server:
    """Запускает сервер в фоновом потоке."""
    threading.Thread(target=server.run, daemon=True).start()
    return server


def start_server(app, port: int) -> uvicorn.Server:
    """Поднимает uvicorn в фоновом потоке, чтобы окно открылось сразу."""
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    return serve(uvicorn.Server(config))


def warm_up(seconds: float = 2.0) -> str:
    """Даёт серверу занять порт и возвращает адрес кабинета."""
    time.sleep(seconds)
    return URL


def create_window(url: str, api):
    """Создаёт нативное окно WebView2 с мостом в JS."""
    return webview.create_window(
        TITLE,
        url,
        width=1440,
        height=920,
        min_size=(1180, 720),
        background_color="#fffdf7",
        js_api=api,
    )


def attach(api, url: str):
    """Создаёт окно и привязывает его к мосту."""
    api.set_window(create_window(url, api))
    return api


def start_gui(api):
    """Показывает окно и запускает цикл событий GUI."""
    return webview.start()


def run_webview(url: str):
    """Показывает нативное окно с панелью функций."""
    return start_gui(attach(DesktopApi(), url))


def run_app_window(url: str) -> int:
    """Открывает кабинет окном браузера без адресной строки и ждёт закрытия."""
    profile = Path(tempfile.gettempdir()) / "magnit-portfolio-window"
    return subprocess.call(
        [
            str(browser_path()),
            f"--app={url}",
            "--window-size=1440,920",
            f"--user-data-dir={profile}",
            "--no-first-run",
            "--no-default-browser-check",
        ]
    )


def launch(mode: str):
    """Запускает шлюз и открывает кабинет выбранным способом."""
    start_server(gateway_app, PORT)
    return run_webview(warm_up()) if mode == "webview" else run_app_window(warm_up())


def add_mode(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """Добавляет выбор режима окна."""
    parser.add_argument("--mode", choices=("webview", "app"), default="webview")
    return parser


def add_port(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """Добавляет порт шлюза."""
    parser.add_argument("--port", type=int, default=PORT)
    return parser


def add_arguments(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """Добавляет все флаги приложения."""
    return add_port(add_mode(parser))


def build_parser() -> argparse.ArgumentParser:
    """Создаёт парсер аргументов приложения."""
    parser = argparse.ArgumentParser(description="ML-кабинет Магнит доставки в отдельном окне")
    return add_arguments(parser)


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Разбирает режим запуска и порт."""
    return build_parser().parse_args(argv)


def main(argv: list[str]) -> int:
    """Точка входа приложения."""
    return launch(parse_args(argv).mode) or 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
