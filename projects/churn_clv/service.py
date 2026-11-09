"""Отток и CLV: RFM-сегменты, логистическая модель удержания и ценность клиента.

Смысл для бизнеса: доставка решает, куда вкладывать удержание, а не только скидки.
CLV на 12 месяцев = частота заказов × чек × маржа × вероятность остаться клиентом.
"""

from functools import lru_cache

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from shared import dataset

FEATURES = ("days_since_order", "orders_30d", "gmv_30d", "app_installed", "promo_sensitivity")
SEGMENT_NAMES = ("Чемпионы", "Лояльные", "Под риском", "Засыпающие", "Потерянные")
PAGE = {
    "title": "Churn & CLV",
    "slug": "churn-clv",
    "eyebrow": "Проект 05 · Клиентская ценность",
    "lead": "RFM-сегментация, вероятность удержания и CLV на 12 месяцев: кому стоит "
    "вкладываться в удержание, а кого дешевле вернуть промокодом.",
    "chips": [
        {"name": "Сегменты", "value": "RFM по recency, frequency, monetary"},
        {"name": "Модель", "value": "логистическая регрессия оттока"},
        {"name": "Стек", "value": "Python, scikit-learn, pandas"},
    ],
}


def churn_signal(frame: pd.DataFrame) -> np.ndarray:
    """Вероятность уйти: давность заказа, частота и наличие приложения."""
    return dataset.sigmoid(
        -2.6
        + 0.028 * frame.days_since_order
        - 0.35 * frame.orders_30d
        - 0.40 * frame.app_installed
        + 0.8 * (1 - frame.promo_sensitivity)
    )


def with_churn(users: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Размечает клиентов наблюдаемым фактом оттока."""
    return users.assign(churned=rng.binomial(1, churn_signal(users)))


def make_base(n: int = 2500, seed: int = 9) -> pd.DataFrame:
    """Клиентская база с оттоком для расчёта CLV."""
    rng = np.random.default_rng(seed)
    return with_churn(dataset.make_users(n, rng), rng)


def rfm_scores(frame: pd.DataFrame) -> pd.DataFrame:
    """RFM-оценки от 1 до 5: свежесть, частота и деньги."""
    return pd.DataFrame(
        {
            "recency": pd.qcut(-frame.days_since_order, 5, labels=False, duplicates="drop") + 1,
            "frequency": pd.qcut(
                frame.orders_30d.rank(method="first"), 5, labels=False, duplicates="drop"
            )
            + 1,
            "monetary": pd.qcut(
                frame.gmv_30d.rank(method="first"), 5, labels=False, duplicates="drop"
            )
            + 1,
        }
    )


def segments_of(scores: pd.DataFrame) -> np.ndarray:
    """Правила сегментации по RFM-оценкам."""
    recency, frequency, monetary = scores.recency, scores.frequency, scores.monetary
    return np.select(
        [
            (recency >= 4) & (frequency >= 4) & (monetary >= 4),
            (recency >= 3) & (frequency >= 4),
            (recency <= 2) & (frequency >= 4),
            (recency <= 2) & (frequency >= 2),
            recency <= 2,
        ],
        list(SEGMENT_NAMES),
        default="Новички",
    )


def churn_model(frame: pd.DataFrame) -> LogisticRegression:
    """Логистическая модель вероятности оттока."""
    return LogisticRegression(max_iter=400, random_state=0).fit(
        frame[list(FEATURES)], frame.churned
    )


def retention(frame: pd.DataFrame) -> np.ndarray:
    """Вероятность остаться клиентом на горизонте 12 месяцев."""
    probability = churn_model(frame).predict_proba(frame[list(FEATURES)])[:, 1]
    return 1 - probability


def base_scored(frame: pd.DataFrame) -> pd.DataFrame:
    """Добавляет вероятность удержания."""
    return frame.assign(retention=retention(frame))


def with_segments(frame: pd.DataFrame) -> pd.DataFrame:
    """Добавляет RFM-сегмент."""
    return frame.assign(segment=segments_of(rfm_scores(frame)))


def with_value(frame: pd.DataFrame) -> pd.DataFrame:
    """Считает CLV на 12 месяцев в рублях."""
    return frame.assign(
        clv=frame.orders_30d * 12 * frame.basket_size * frame.margin_rate * frame.retention
    )


def scored_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Полная витрина: удержание, сегмент и CLV."""
    return with_value(with_segments(base_scored(frame)))


@lru_cache(maxsize=1)
def table() -> pd.DataFrame:
    """Витрина клиентов, посчитанная один раз на процесс."""
    return scored_frame(make_base())


def summary() -> dict[str, float]:
    """Сводка: размер базы, CLV, отток и ценность клиентов под риском."""
    frame = table()
    return {
        "customers": len(frame),
        "total_clv": round(float(frame.clv.sum()), 2),
        "avg_clv": round(float(frame.clv.mean()), 2),
        "at_risk_clv": round(float(frame.loc[frame.segment == "Под риском", "clv"].sum()), 2),
        "churn_rate": round(float(frame.churned.mean()), 3),
        "retention": round(float(frame.retention.mean()), 3),
    }


def segments_table() -> list[dict]:
    """Агрегаты по сегментам: клиенты, CLV, отток, удержание."""
    grouped = (
        table()
        .groupby("segment", as_index=False)
        .agg(
            customers=("user_id", "size"),
            avg_clv=("clv", "mean"),
            total_clv=("clv", "sum"),
            churn_rate=("churned", "mean"),
            retention=("retention", "mean"),
        )
    )
    return grouped.sort_values("total_clv", ascending=False).round(3).to_dict("records")


def top_customers(limit: int = 12) -> list[dict]:
    """Самые ценные клиенты по CLV."""
    columns = ["user_id", "segment", "orders_30d", "days_since_order", "retention", "clv"]
    return (
        table().sort_values("clv", ascending=False).head(limit)[columns].round(3).to_dict("records")
    )
