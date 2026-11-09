"""Кабинет: сводка по всем моделям и промо-контуру в одном отчёте.

Кабинет не дублирует расчёты, а берёт готовые ответы сервисов: uplift-модель,
план распределения промокодов, результат A/B, состояние пайплайна, CLV,
дрейф и SQL-витрину. Один вызов — один экран для руководителя.
"""

from datetime import datetime
from functools import lru_cache

from projects.ab_lab import service as ab
from projects.churn_clv import service as churn
from projects.ml_monitor import service as monitor
from projects.ml_pipeline import service as pipeline
from projects.promo_optimizer import service as promo
from projects.sql_lab import service as sql
from projects.uplift_engine import service as uplift

PAGE = {
    "title": "ML-кабинет",
    "slug": "cabinet",
    "eyebrow": "Магнит доставка · сводка ML-контура",
    "lead": "Один экран по всем моделям: качество uplift, эффект промо-плана, статус A/B, "
    "пайплайна, клиентской ценности, дрейфа и витрины заказов.",
    "chips": [
        {"name": "Источник", "value": "API семи сервисов"},
        {"name": "Обновление", "value": "по кнопке, кэш на процесс"},
        {"name": "Формат", "value": "кабинет руководителя"},
    ],
}


def money(value: float) -> str:
    """Форматирует сумму в рублях с пробелами между разрядами."""
    return f"{value:,.0f}".replace(",", " ") + " ₽"


def card(slug: str, title: str, label: str, value: str, status: str, detail: str) -> dict:
    """Карточка раздела кабинета."""
    return {
        "slug": slug,
        "title": title,
        "label": label,
        "value": value,
        "status": status,
        "detail": detail,
        "href": f"/p/{slug}/",
    }


def uplift_card() -> dict:
    """Качество uplift-модели на отложенной выборке."""
    data = uplift.bundle()
    return card(
        "uplift-engine",
        "Uplift Engine",
        "AUUC на holdout",
        f"{data['metrics']['two_model']['auuc']:.1f}",
        "ok",
        f"{data['holdout_size']} пользователей в проверке",
    )


def promo_card() -> dict:
    """Эффект оптимизированного плана промокодов."""
    data = promo.optimize()
    return card(
        "promo-optimizer",
        "Promo Optimizer",
        "Инкрементальная CM2",
        money(data["plan"]["incremental_cm2"]),
        "ok" if data["plan"]["roi"] > 0 else "warn",
        f"CPO {money(data['plan']['cpo'])}, охват {data['plan']['users']} клиентов",
    )


def ab_card() -> dict:
    """Результат последнего эксперимента."""
    data = ab.report(ab.data())
    return card(
        "ab-lab",
        "A/B Lab",
        "Эффект после CUPED",
        money(data["cuped"]["diff"]),
        "ok" if data["cuped"]["p_value"] < 0.05 else "warn",
        f"p = {data['cuped']['p_value']:.4f}, дисперсия срезана на {data['reduction']:.0%}",
    )


def pipeline_card_of(state: dict) -> dict:
    """Карточка пайплайна по сохранённому манифесту."""
    stages = state["stages"]
    return card(
        "ml-pipeline",
        "ML Pipeline",
        "Последний прогон",
        f"{len(stages)} стадий" if stages else "не запускался",
        "ok" if stages else "warn",
        "кэш по хешам входов" if stages else "нужен первый запуск",
    )


def pipeline_card() -> dict:
    """Состояние стадий обучения и скоринга."""
    return pipeline_card_of(pipeline.state())


def churn_card() -> dict:
    """Ценность клиентской базы."""
    data = churn.summary()
    return card(
        "churn-clv",
        "Churn & CLV",
        "CLV базы за 12 месяцев",
        money(data["total_clv"]),
        "ok",
        f"удержание {data['retention']:.0%}, под риском {money(data['at_risk_clv'])}",
    )


def monitor_card() -> dict:
    """Алерты по дрейфу данных, имитируем сдвиг спроса ×1.4."""
    data = monitor.summary(1.4)
    return card(
        "ml-monitor",
        "ML Monitor",
        "Признаков в алерте",
        str(data["flagged"]),
        "ok" if data["flagged"] == 0 else "warn",
        f"максимальный PSI {data['max_psi']:.3f}",
    )


def sql_totals() -> tuple[int, float]:
    """Число заказов и GMV витрины."""
    data = sql.run_query("SELECT count(*) AS orders, round(sum(gmv), 0) AS gmv FROM orders")
    return data["rows"][0]


def sql_card() -> dict:
    """Объём витрины заказов."""
    orders, gmv = sql_totals()
    return card(
        "sql-lab",
        "SQL Metrics Lab",
        "Заказов в витрине",
        f"{int(orders):,}".replace(",", " "),
        "ok",
        f"GMV витрины {money(gmv)}",
    )


BUILDERS = (uplift_card, promo_card, ab_card, pipeline_card, churn_card, monitor_card, sql_card)


def build_overview() -> dict:
    """Собирает карточки всех разделов и общую сводку."""
    cards = [builder() for builder in BUILDERS]
    return {
        "cards": cards,
        "generated_at": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "alerts": sum(1 for item in cards if item["status"] != "ok"),
        "sections": len(cards),
    }


@lru_cache(maxsize=1)
def overview() -> dict:
    """Сводка кабинета с кэшем на процесс."""
    return build_overview()


def fresh(refresh: bool = False) -> dict:
    """Сводка с возможностью принудительного пересчёта."""
    if refresh:
        overview.cache_clear()
    return overview()
