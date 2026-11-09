"""Запись демо-гифок интерфейса через Playwright: кадры снимаются, GIF собирает Pillow.

Запуск:
    python -m tools.record_demo

Скрипт поднимает шлюз на 127.0.0.1:8770, проходит по разделам кабинета,
снимает кадры и складывает два GIF в docs/screens/.
"""

import threading
import time
from pathlib import Path

import uvicorn
from PIL import Image
from playwright.sync_api import sync_playwright

from gateway.app import app as gateway_app

PORT = 8770
BASE = f"http://127.0.0.1:{PORT}"
OUT = Path(__file__).resolve().parents[1] / "docs" / "screens"
FRAMES = Path(__file__).resolve().parents[1] / "docs" / "frames"
VIEWPORT = {"width": 1280, "height": 860}
GIF_WIDTH = 1000
WAIT = 2500

CABINET_STEPS = (
    ("cabinet-1", "/", None),
    ("cabinet-2", "/", "#refresh"),
)

TOUR_STEPS = (
    ("tour-1-cabinet", "/", None),
    ("tour-2-uplift", "/p/uplift-engine/", None),
    ("tour-3-promo", "/p/promo-optimizer/", "#run"),
    ("tour-4-ab", "/p/ab-lab/", "#calc"),
    ("tour-5-monitor", "/p/ml-monitor/", "#recalc"),
    ("tour-6-sql", "/p/sql-lab/", "#presets button"),
)


def server_config(port: int) -> uvicorn.Config:
    """Конфигурация uvicorn для фонового шлюза."""
    return uvicorn.Config(gateway_app, host="127.0.0.1", port=port, log_level="warning")


def serve(server: uvicorn.Server) -> uvicorn.Server:
    """Запускает сервер в фоновом потоке."""
    threading.Thread(target=server.run, daemon=True).start()
    return server


def start_server() -> uvicorn.Server:
    """Поднимает шлюз в фоновом потоке."""
    return serve(uvicorn.Server(server_config(PORT)))


def goto(page, path: str):
    """Открывает страницу и ждёт, пока отработают запросы к API."""
    page.goto(BASE + path, wait_until="networkidle", timeout=180_000)
    return page


def pause(page, milliseconds: int = WAIT):
    """Пауза, чтобы отрисовались графики и таблицы."""
    page.wait_for_timeout(milliseconds)
    return page


def click(page, selector: str):
    """Нажимает кнопку и ждёт отрисовки результата."""
    page.click(selector, timeout=60_000)
    return pause(page)


def act(page, step, folder: Path):
    """Снимает кадр и при необходимости нажимает кнопку шага."""
    page.screenshot(path=str(folder / f"{step[0]}.png"))
    return click(page, step[2]) if step[2] else page


def shoot(page, step, folder: Path):
    """Дожидается отрисовки и делает кадр шага."""
    return act(pause(page), step, folder)


def capture(page, step, folder: Path):
    """Открывает страницу шага и снимает кадр."""
    goto(page, step[1])
    return shoot(page, step, folder)


def record(page, steps, folder: Path) -> list[Path]:
    """Проходит сценарий и возвращает пути кадров."""
    [capture(page, step, folder) for step in steps]
    return sorted(folder.glob("*.png"))


def scaled(path: Path, width: int = GIF_WIDTH) -> Image.Image:
    """Открывает кадр и приводит к ширине гифки."""
    image = Image.open(path).convert("RGB")
    return image.resize((width, int(image.height * width / image.width)), Image.Resampling.LANCZOS)


def save_gif(images: list[Image.Image], target: Path, duration: int) -> Path:
    """Сохраняет последовательность кадров как зацикленный GIF."""
    images[0].save(
        target, save_all=True, append_images=images[1:], duration=duration, loop=0, optimize=True
    )
    return target


def make_gif(frames: list[Path], target: Path, duration: int = 1100) -> Path:
    """Собирает GIF из кадров с палитрой 128 цветов."""
    return save_gif([scaled(path).quantize(colors=128) for path in frames], target, duration)


def clear(folder: Path) -> Path:
    """Удаляет старые кадры, чтобы гифка не тянула прошлый прогон."""
    [path.unlink() for path in folder.glob("*.png")]
    return folder


def make_dir(folder: Path) -> Path:
    """Создаёт каталог кадров."""
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def prepare(name: str) -> Path:
    """Готовит каталог кадров для сценария."""
    return clear(make_dir(FRAMES / name))


def scenario(page, steps, name: str) -> Path:
    """Снимает сценарий и собирает из кадров гифку."""
    folder = prepare(name)
    return make_gif(record(page, steps, folder), OUT / f"{name}.gif")


def run_browser() -> list[Path]:
    """Запускает браузер и записывает обе гифки."""
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="chrome", headless=True)
        page = browser.new_page(viewport=VIEWPORT, device_scale_factor=1)
        results = [
            scenario(page, CABINET_STEPS, "demo-cabinet"),
            scenario(page, TOUR_STEPS, "demo-tour"),
        ]
        browser.close()
    return results


def report(paths: list[Path]) -> int:
    """Печатает размеры готовых гифок."""
    print("\n".join(f"{path.name}: {path.stat().st_size // 1024} КБ" for path in paths))
    return 0


def wait_ready(server) -> object:
    """Даёт шлюзу занять порт."""
    time.sleep(3)
    return server


def prepare_run():
    """Поднимает шлюз и даёт ему занять порт."""
    return wait_ready(start_server())


def main() -> int:
    """Точка входа: сервер, запись, отчёт."""
    prepare_run()
    return report(run_browser())


if __name__ == "__main__":
    raise SystemExit(main())
