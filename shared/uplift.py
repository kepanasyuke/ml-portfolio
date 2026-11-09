"""Uplift-моделирование промокодов: две модели, transformed outcome и метрики качества.

Терминология из вакансии: uplift (CATE), Qini, AUUC, uplift@k.
Метрики считаются по ранжированию, а не по абсолютной вероятности, поэтому
сравнивать модели корректно на одном и том же экспериментальном срезе.
"""

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier

SEGMENT_CODE = {"new": 0, "loyal": 1, "sleeping": 2, "vip": 3, "builder": 4}
CITY_CODE = {"Москва": 0, "Санкт-Петербург": 1, "Краснодар": 2, "Казань": 3, "Екатеринбург": 4}
NUMERIC = (
    "age",
    "orders_30d",
    "days_since_order",
    "basket_size",
    "margin_rate",
    "app_installed",
    "promo_sensitivity",
    "promo_value",
)


@dataclass(frozen=True)
class UpliftPair:
    """Пара моделей: отклик в тесте и отклик в контроле."""

    treated: Any
    control: Any


def model() -> HistGradientBoostingClassifier:
    """Быстрая бустинг-модель отклика с фиксированным seed."""
    return HistGradientBoostingClassifier(
        random_state=0, max_iter=160, max_depth=3, learning_rate=0.07, l2_regularization=0.2
    )


def design_matrix(frame: pd.DataFrame) -> np.ndarray:
    """Числовая матрица признаков с ординальным кодированием сегмента и города."""
    return np.column_stack(
        [
            frame[list(NUMERIC)].to_numpy(dtype=float),
            frame["segment"].map(SEGMENT_CODE).to_numpy(dtype=float),
            frame["city"].map(CITY_CODE).to_numpy(dtype=float),
        ]
    )


def fit_classifier(frame: pd.DataFrame) -> Any:
    """Обучает модель вероятности заказа на подвыборке."""
    return model().fit(design_matrix(frame), frame["converted"])


def fit_two_model(frame: pd.DataFrame) -> UpliftPair:
    """Двухмодельный uplift: отдельные модели для теста и контроля."""
    return UpliftPair(
        fit_classifier(frame[frame.treated == 1]), fit_classifier(frame[frame.treated == 0])
    )


def predict_uplift(pair: UpliftPair, frame: pd.DataFrame) -> np.ndarray:
    """CATE как разница предсказанных вероятностей теста и контроля."""
    matrix = design_matrix(frame)
    return pair.treated.predict_proba(matrix)[:, 1] - pair.control.predict_proba(matrix)[:, 1]


def fit_transformed(frame: pd.DataFrame) -> Any:
    """Transformed outcome: одна модель с treatment как признаком."""
    return model().fit(
        np.column_stack([design_matrix(frame), frame["treated"]]), frame["converted"]
    )


def predict_transformed(transformer: Any, frame: pd.DataFrame) -> np.ndarray:
    """CATE из одной модели: отклик при treatment=1 минус treatment=0."""
    matrix = design_matrix(frame)
    return (
        transformer.predict_proba(np.column_stack([matrix, np.ones(len(matrix))]))[:, 1]
        - transformer.predict_proba(np.column_stack([matrix, np.zeros(len(matrix))]))[:, 1]
    )


def ranked(uplift: np.ndarray, treated: np.ndarray, converted: np.ndarray) -> pd.DataFrame:
    """Пользователи в порядке убывания предсказанного uplift."""
    order = np.argsort(-np.asarray(uplift, dtype=float))
    return pd.DataFrame(
        {"treated": np.asarray(treated)[order], "converted": np.asarray(converted)[order]}
    )


def cumulative(rank: pd.DataFrame) -> pd.DataFrame:
    """Накопленные конверсии и размеры групп по префиксам ранжирования."""
    return rank.assign(
        conv_t=(rank.treated * rank.converted).cumsum(),
        conv_c=((1 - rank.treated) * rank.converted).cumsum(),
        size_t=rank.treated.cumsum(),
        size_c=(1 - rank.treated).cumsum(),
    )


def qini_values(cum: pd.DataFrame) -> pd.Series:
    """Qini по каждому префиксу: инкремент конверсий против масштабированного контроля."""
    return cum.conv_t - cum.conv_c * cum.size_t / cum.size_c.replace(0, np.nan)


def grid_positions(size: int, points: int) -> np.ndarray:
    """Равномерные позиции префиксов для отрисовки кривой."""
    return np.unique(np.linspace(1, size, min(points, size)).astype(int))


def select_grid(cum: pd.DataFrame, grid: np.ndarray) -> pd.DataFrame:
    """Срез накопленных значений по сетке префиксов."""
    return pd.DataFrame(
        {
            "share": grid / len(cum),
            "qini": qini_values(cum).to_numpy()[grid - 1],
            "users": grid,
            "treated": cum.size_t.to_numpy()[grid - 1],
        }
    ).dropna()


def qini_curve(
    uplift: np.ndarray, treated: np.ndarray, converted: np.ndarray, points: int = 80
) -> pd.DataFrame:
    """Кривая Qini для отрисовки на дашборде."""
    cum = cumulative(ranked(uplift, treated, converted))
    return select_grid(cum, grid_positions(len(cum), points))


def auuc(uplift: np.ndarray, treated: np.ndarray, converted: np.ndarray) -> float:
    """Площадь под кривой Qini: интегральная метрика качества ранжирования."""
    curve = qini_curve(uplift, treated, converted)
    return float(np.trapezoid(curve.qini, curve.share))


def group_rate(frame: pd.DataFrame) -> float:
    """Доля конверсий в подгруппе с защитой от пустой выборки."""
    return float(frame["converted"].mean()) if len(frame) else 0.0


def uplift_at_share(
    uplift: np.ndarray, treated: np.ndarray, converted: np.ndarray, share: float = 0.1
) -> float:
    """Uplift@k: инкремент конверсии в топ-доле аудитории по предсказанию."""
    top = ranked(uplift, treated, converted).head(max(int(len(treated) * share), 1))
    return group_rate(top[top.treated == 1]) - group_rate(top[top.treated == 0])


def summarize_deciles(frame: pd.DataFrame) -> pd.DataFrame:
    """Сводит ранжирование в таблицу по децилям с фактическим uplift."""
    grouped = frame.groupby("decile").apply(
        lambda part: pd.Series(
            {
                "treated_rate": group_rate(part[part.treated == 1]),
                "control_rate": group_rate(part[part.treated == 0]),
                "conversions": float(part.converted.sum()),
                "users": float(len(part)),
            }
        ),
        include_groups=False,
    )
    return grouped.assign(uplift=grouped.treated_rate - grouped.control_rate).reset_index()


def decile_report(
    uplift: np.ndarray, treated: np.ndarray, converted: np.ndarray, deciles: int = 10
) -> pd.DataFrame:
    """Отчёт по децилям: первый дециль — самая перспективная аудитория."""
    return summarize_deciles(
        ranked(uplift, treated, converted).assign(
            decile=lambda data: pd.qcut(data.index, deciles, labels=False) + 1
        )
    )
