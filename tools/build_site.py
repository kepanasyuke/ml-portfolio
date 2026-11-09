"""Статическая сборка кабинета для GitHub Pages.

Поднимает шлюз (или берёт уже запущенный), обходит страницы, скачивает статику
и ответы API в каталог site/, подставляя префикс проекта в абсолютные ссылки.

Запуск:
    python -m tools.build_site
"""

import re
import urllib.request
from contextlib import suppress
from pathlib import Path

BASE = "http://127.0.0.1:8150"
PREFIX = "/ml-portfolio"
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "site"
SLUGS = (
    "uplift-engine",
    "promo-optimizer",
    "ab-lab",
    "ml-pipeline",
    "churn-clv",
    "ml-monitor",
    "sql-lab",
)


def routes() -> list[str]:
    """Адреса страниц кабинета и разделов."""
    return ["/"] + [f"/p/{slug}/" for slug in SLUGS]


def fetch(url: str) -> bytes:
    """Забирает байты по адресу."""
    return urllib.request.urlopen(url, timeout=120).read()


def save(path: Path, data: bytes) -> Path:
    """Пишет файл, создавая каталоги."""
    path.parent.mkdir(parents=True, exist_ok=True)
    return path.write_bytes(data) or path


def grab(path: str) -> Path:
    """Скачивает файл сайта в сборку по тому же относительному пути."""
    return save(OUT / path.lstrip("/"), fetch(BASE + path))


def prefix(html: str) -> str:
    """Переписывает абсолютные ссылки под подкаталог GitHub Pages."""
    return html.replace('href="/', f'href="{PREFIX}/').replace('src="/', f'src="{PREFIX}/')


def assets(html: str) -> list[str]:
    """Ссылки на стили, скрипты и картинки страницы."""
    return sorted(
        {
            url
            for url in re.findall(r'(?:href|src)="(/[^"]+)"', html)
            if "/static/" in url or "/assets/" in url
        }
    )


def styles(html: str) -> list[str]:
    """Стили страницы."""
    return [url for url in assets(html) if url.endswith(".css")]


def css_urls(path: str, source: str) -> list[str]:
    """Файлы, на которые ссылаются стили через url()."""
    folder = path.rsplit("/", 1)[0]
    return sorted(
        {
            f"{folder}/{name}"
            for name in re.findall(r'url\("([^"]+)"\)', source)
            if ":" not in name
        }
    )


def css_assets(html: str) -> list[Path]:
    """Скачивает картинки, на которые ссылаются стили страницы."""
    return [grab(url) for css in styles(html) for url in css_urls(css, js_source(css))]


def scripts(html: str) -> list[str]:
    """Скрипты страницы."""
    return [url for url in assets(html) if url.endswith(".js")]

def endpoints(source: str) -> list[str]:
    """Эндпоинты, которые страница запрашивает относительным fetch."""
    return sorted({path.split("?")[0] for path in re.findall(r'fetch\("(api/[^"]+)"', source)})


def collect(url: str, sink: dict[str, bytes]) -> bytes:
    """Читает ответ, не падая на POST-эндпоинтах и ошибках."""
    with suppress(OSError, urllib.error.HTTPError):
        sink["body"] = fetch(url)
    return sink.get("body", b"")


def bodies(base: str, names: list[str]) -> dict[str, bytes]:
    """Тела доступных GET-эндпоинтов страницы."""
    return {name: collect(BASE + base + name, {}) for name in names}


def api_files(base: str, source: str) -> list[Path]:
    """Сохраняет JSON-ответы API рядом со страницей."""
    folder = OUT / base.strip("/")
    return [save(folder / n, body) for n, body in bodies(base, endpoints(source)).items() if body]


def js_source(path: str) -> str:
    """Текст скрипта для поиска запросов."""
    return fetch(BASE + path).decode("utf-8")


def build_page(base: str) -> list[Path]:
    """Собирает одну страницу вместе со статикой и данными."""
    html = fetch(BASE + base).decode("utf-8")
    return [
        save(OUT / base.strip("/") / "index.html", prefix(html).encode("utf-8")),
        *[grab(url) for url in assets(html)],
        *css_assets(html),
        *[path for js in scripts(html) for path in api_files(base, js_source(js))],
    ]


def nojekyll() -> Path:
    """Отключает обработку Jekyll на GitHub Pages."""
    return save(OUT / ".nojekyll", b"")


def build_all() -> int:
    """Собирает все страницы и служебные файлы."""
    pages = [build_page(base) for base in routes()]
    return 0 if nojekyll() and pages else 1


def main() -> int:
    """Точка входа сборки."""
    return build_all()


if __name__ == "__main__":
    raise SystemExit(main())
