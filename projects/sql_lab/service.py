"""SQL-лаборатория: заказы доставки в SQLite, запросы в синтаксисе Trino/ClickHouse.

В вакансии это «уверенный SQL плюс Trino и ClickHouse». Здесь запросы пишутся в
аналитическом диалекте (date_trunc, approx_distinct), а исполняются локально на SQLite
через шим: без внешних сервисов, но с реальными бизнес-метриками GMV, CM2 и CPO.
"""

import re
import sqlite3
import time
from functools import reduce
from pathlib import Path

import numpy as np
import pandas as pd

from shared import dataset

DB = Path(__file__).resolve().parent / ".local_s3" / "orders.db"
LIMIT = 200
PAGE = {
    "title": "SQL Metrics Lab",
    "slug": "sql-lab",
    "eyebrow": "Проект 07 · SQL и бизнес-метрики",
    "lead": "Витрина заказов доставки и аналитические запросы: GMV, CM2, CPO и динамика "
    "по городам, категориям и неделям — в синтаксисе Trino/ClickHouse на локальном движке.",
    "chips": [
        {"name": "Диалект", "value": "Trino / ClickHouse (шим на SQLite)"},
        {"name": "Метрики", "value": "GMV, CM2, CPO, маржа"},
        {"name": "Стек", "value": "Python, SQLite, pandas, FastAPI"},
    ],
}

SHIMS = (
    (r"date_trunc\('week',\s*([^)]+)\)", r"strftime('%Y-%W', \1)"),
    (r"date_trunc\('month',\s*([^)]+)\)", r"strftime('%Y-%m', \1)"),
    (r"approx_distinct\(", "count(distinct "),
    (r"toStartOfWeek\(([^)]+)\)", r"strftime('%Y-%W', \1)"),
)

PRESETS = [
    {
        "name": "GMV, CM2 и CPO по городам",
        "sql": """SELECT city,
       round(sum(gmv), 2) AS gmv,
       round(sum(gmv * margin_rate - delivery_cost), 2) AS cm2,
       round(sum(promo_cost) / nullif(count(*), 0), 2) AS cpo
FROM orders
GROUP BY city
ORDER BY gmv DESC""",
    },
    {
        "name": "Недельная динамика заказов",
        "sql": """SELECT date_trunc('week', order_date) AS week,
       count(*) AS orders,
       round(sum(gmv), 2) AS gmv,
       round(avg(gmv), 2) AS avg_check
FROM orders
GROUP BY 1
ORDER BY 1""",
    },
    {
        "name": "Промо против органики",
        "sql": """SELECT CASE WHEN promo_cost > 0 THEN 'promo' ELSE 'organic' END AS channel,
       count(*) AS orders,
       round(avg(gmv), 2) AS avg_gmv,
       round(sum(gmv * margin_rate - delivery_cost), 2) AS cm2
FROM orders
GROUP BY 1
ORDER BY cm2 DESC""",
    },
    {
        "name": "Категории по вкладу в CM2",
        "sql": """SELECT category,
       count(*) AS orders,
       round(sum(gmv), 2) AS gmv,
       round(sum(gmv * margin_rate - delivery_cost), 2) AS cm2,
       round(avg(margin_rate), 3) AS margin_rate
FROM orders
GROUP BY category
ORDER BY cm2 DESC""",
    },
    {
        "name": "Маржа и чек по сегментам",
        "sql": """SELECT segment,
       count(*) AS orders,
       round(avg(gmv), 2) AS avg_check,
       round(avg(margin_rate), 3) AS margin_rate,
       approx_distinct(user_id) AS users
FROM orders
GROUP BY segment
ORDER BY avg_check DESC""",
    },
]


def draw_orders(gen: np.random.Generator, users: pd.DataFrame) -> pd.DataFrame:
    """Заказы доставки: город, категория, дата, GMV и затраты."""
    return pd.DataFrame(
        {
            "order_id": np.arange(1, len(users) + 1),
            "user_id": users.user_id.to_numpy(),
            "city": users.city.to_numpy(),
            "segment": users.segment.to_numpy(),
            "category": gen.choice(("Молочное", "Овощи", "Мясо", "Бакалея", "Готовое"), len(users)),
            "order_date": pd.Timestamp("2026-09-01")
            + pd.to_timedelta(gen.integers(0, 35, len(users)), unit="D"),
            "gmv": users.basket_size.to_numpy(),
            "margin_rate": users.margin_rate.to_numpy(),
            "delivery_cost": users.delivery_cost.to_numpy(),
            "promo_cost": np.where(
                gen.random(len(users)) < 0.55, gen.choice([100, 200, 300, 500], len(users)), 0
            ),
        }
    )


def orders_frame(n: int = 6000, seed: int = 13) -> pd.DataFrame:
    """Синтетическая витрина заказов доставки."""
    gen = np.random.default_rng(seed)
    return draw_orders(gen, dataset.make_users(n, gen))


def load_orders(conn: sqlite3.Connection) -> sqlite3.Connection:
    """Заливает витрину заказов в SQLite."""
    orders_frame().to_sql("orders", conn, if_exists="replace", index=False)
    return conn


def connection() -> sqlite3.Connection:
    """Создаёт файл витрины и возвращает соединение SQLite."""
    DB.parent.mkdir(parents=True, exist_ok=True)
    return load_orders(sqlite3.connect(DB, check_same_thread=False))


CONN = connection()


def translate(sql: str) -> str:
    """Переводит функции Trino/ClickHouse в эквиваленты SQLite."""
    return reduce(
        lambda text, pair: re.sub(pair[0], pair[1], text, flags=re.IGNORECASE), SHIMS, sql
    )


def guard(sql: str) -> dict:
    """Пропускает только одиночный read-only запрос."""
    cleaned = re.sub(r"--[^\n]*", " ", sql).strip().rstrip(";")
    return {
        "ok": cleaned.lower().startswith(("select", "with")) and ";" not in cleaned,
        "sql": cleaned,
    }


def refused() -> dict:
    """Ответ на запрос, нарушающий read-only контракт."""
    return {
        "error": "Разрешены только одиночные SELECT/WITH-запросы",
        "columns": [],
        "rows": [],
        "ms": 0.0,
    }


def shape(frame: pd.DataFrame, guarded: dict, started: float) -> dict:
    """Приводит результат запроса к JSON-виду."""
    return {
        "columns": [str(column) for column in frame.columns],
        "rows": frame.round(2).to_numpy().tolist(),
        "ms": round((time.perf_counter() - started) * 1000, 1),
        "sql": translate(guarded["sql"]),
        "count": len(frame),
    }


def read_frame(guarded: dict) -> pd.DataFrame:
    """Читает результат запроса с ограничением на размер выдачи."""
    return pd.read_sql_query(f"{translate(guarded['sql'])} LIMIT {LIMIT}", CONN)


def execute_sql(guarded: dict) -> dict:
    """Выполняет подготовленный запрос с ограничением на размер выдачи."""
    started = time.perf_counter()
    return shape(read_frame(guarded), guarded, started)


def run_query(sql: str) -> dict:
    """Публичная точка входа: валидация, трансляция диалекта, выполнение."""
    guarded = guard(sql)
    return execute_sql(guarded) if guarded["ok"] else refused()


def presets() -> list[dict]:
    """Готовые бизнес-запросы для дашборда."""
    return PRESETS


def schema() -> list[dict]:
    """Описание колонок витрины orders для подсказки на странице."""
    frame = pd.read_sql_query("PRAGMA table_info(orders)", CONN)
    return [{"name": row["name"], "type": row["type"]} for _, row in frame.iterrows()]
