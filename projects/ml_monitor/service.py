"""ML-мониторинг: PSI и KS по признакам, дрейф скорингов и алерты.

Задача из вакансии — «опыт построения ML-мониторинга». Здесь показан контур:
эталонная выборка из обучения против текущего батча, пороги PSI, алерты по признакам
и отдельный контроль распределения предсказаний модели.
"""

from functools import lru_cache

import numpy as np
import pandas as pd
from scipy.stats import ks_2samp

from shared import dataset, uplift

EPS = 1e-6
FEATURES = (
    "gmv_30d",
    "basket_size",
    "orders_30d",
    "days_since_order",
    "margin_rate",
    "promo_value",
)
THRESHOLDS = {"ok": 0.10, "warn": 0.25}
PAGE = {
    "title": "ML Monitor",
    "slug": "ml-monitor",
    "eyebrow": "Проект 06 · Мониторинг",
    "lead": "Дрейф данных и скорингов: PSI и KS на каждом признаке, алерты по порогам "
    "и контроль распределения предсказаний uplift-модели.",
    "chips": [
        {"name": "Метрики", "value": "PSI, KS-статистика"},
        {"name": "Пороги", "value": "0.10 / 0.25"},
        {"name": "Стек", "value": "Python, scipy, FastAPI"},
    ],
}


@lru_cache(maxsize=1)
def reference() -> pd.DataFrame:
    """Эталонная выборка: то, на чём модель обучалась."""
    return dataset.make_promo_dataset(4000, seed=7)


def shift_frame(ref: pd.DataFrame, factor: float, seed: int = 101) -> pd.DataFrame:
    """Текущий батч со сдвигом спроса: сезон, акция или новая аудитория."""
    rng = np.random.default_rng(seed)
    return ref.assign(
        gmv_30d=ref.gmv_30d * factor,
        basket_size=ref.basket_size * (1 + 0.25 * (factor - 1)),
        orders_30d=np.clip(np.round(ref.orders_30d * (1 + 0.15 * (factor - 1))), 0, None),
        days_since_order=np.clip(
            ref.days_since_order + 15 * (factor - 1) + rng.normal(0, 2, len(ref)), 1, None
        ),
    )


def proportions(values: np.ndarray, edges: np.ndarray) -> np.ndarray:
    """Доли наблюдений в бинах, построенных по эталону."""
    counts = np.histogram(values, edges)[0]
    return counts / max(len(values), 1)


def quantile_edges(expected: np.ndarray, bins: int) -> np.ndarray:
    """Границы бинов по квантилям эталонной выборки."""
    return np.unique(
        np.concatenate(
            ([-np.inf], np.quantile(expected, np.linspace(0, 1, bins + 1))[1:-1], [np.inf])
        )
    )


def divergence(expected: np.ndarray, actual: np.ndarray) -> float:
    """Population Stability Index по долям бинов."""
    return float(np.sum((actual - expected) * np.log((actual + EPS) / (expected + EPS))))


def psi(expected, actual, bins: int = 10) -> float:
    """PSI между эталонным и текущим распределением признака."""
    edges = quantile_edges(np.asarray(expected, dtype=float), bins)
    return divergence(
        proportions(np.asarray(expected, dtype=float), edges),
        proportions(np.asarray(actual, dtype=float), edges),
    )


def status_of(value: float) -> str:
    """Статус признака по порогам PSI."""
    return "ok" if value < THRESHOLDS["ok"] else ("warn" if value < THRESHOLDS["warn"] else "bad")


def feature_row(name: str, ref: pd.DataFrame, cur: pd.DataFrame) -> dict:
    """Строка мониторинга по одному признаку."""
    expected, actual = ref[name].to_numpy(), cur[name].to_numpy()
    return {
        "feature": name,
        "psi": round(psi(expected, actual), 4),
        "ks": round(float(ks_2samp(expected, actual).statistic), 4),
        "ref_mean": round(float(np.mean(expected)), 2),
        "cur_mean": round(float(np.mean(actual)), 2),
    }


def feature_table(ref: pd.DataFrame, cur: pd.DataFrame) -> list[dict]:
    """Таблица дрейфа по всем контролируемым признакам."""
    rows = [feature_row(name, ref, cur) for name in FEATURES]
    return [{**row, "status": status_of(row["psi"])} for row in rows]


def score_row(model, ref: pd.DataFrame, cur: pd.DataFrame) -> dict:
    """Дрейф распределения предсказаний модели."""
    return {
        "psi": round(psi(uplift.predict_uplift(model, ref), uplift.predict_uplift(model, cur)), 4),
        "ref_mean": round(float(uplift.predict_uplift(model, ref).mean()), 4),
        "cur_mean": round(float(uplift.predict_uplift(model, cur).mean()), 4),
    }


def score_drift(ref: pd.DataFrame, cur: pd.DataFrame) -> dict:
    """PSI по скорингам обученной модели."""
    model = uplift.fit_two_model(ref)
    return score_row(model, ref, cur)


def build(ref: pd.DataFrame, cur: pd.DataFrame, factor: float) -> dict:
    """Собирает отчёт мониторинга."""
    features = feature_table(ref, cur)
    return {
        "features": features,
        "scores": score_drift(ref, cur),
        "alerts": [row for row in features if row["status"] != "ok"],
        "meta": {"reference": len(ref), "current": len(cur), "factor": round(factor, 2)},
    }


@lru_cache(maxsize=8)
def report(factor: float = 1.0) -> dict:
    """Отчёт при заданной силе сдвига, с кэшем по значению сдвига."""
    ref = reference()
    return build(ref, shift_frame(ref, factor), factor)


def summary(factor: float = 1.0) -> dict:
    """Сводка для KPI: максимальный PSI, число алертов, дрейф скорингов."""
    data = report(factor)
    return {
        "factor": factor,
        "max_psi": round(max(row["psi"] for row in data["features"]), 4),
        "flagged": len(data["alerts"]),
        "score_psi": data["scores"]["psi"],
        "reference": data["meta"]["reference"],
        "current": data["meta"]["current"],
    }
