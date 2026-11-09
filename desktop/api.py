"""Мост между окном pywebview и страницей: кнопки панели приложения.

Методы класса доступны из JS как window.pywebview.api.<method>. Окно передаётся
отдельно, чтобы мост можно было протестировать без GUI.
"""

import webbrowser
from dataclasses import dataclass


@dataclass
class DesktopApi:
    """Функции окна: полный экран, заголовок, внешний браузер, закрытие."""

    window: object | None = None

    def set_window(self, window) -> "DesktopApi":
        """Привязывает созданное окно к мосту."""
        self.window = window
        return self

    def toggle_fullscreen(self) -> bool:
        """Переключает полноэкранный режим окна."""
        self.window.toggle_fullscreen()
        return True

    def open_browser(self, url: str) -> bool:
        """Открывает текущий раздел во внешнем браузере."""
        webbrowser.open(url)
        return True

    def set_title(self, title: str) -> bool:
        """Обновляет заголовок окна под открытый раздел."""
        self.window.set_title(title)
        return True

    def close(self) -> bool:
        """Закрывает окно приложения."""
        self.window.destroy()
        return True

    def about(self) -> dict:
        """Сведения о приложении для модального окна."""
        return {
            "app": "ML-кабинет Магнит доставки",
            "version": "1.1",
            "stack": "FastAPI · pywebview · WebView2",
            "sections": 7,
            "note": "Данные синтетические, считаются локально по seed.",
        }
