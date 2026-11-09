"""Сервис uplift-модели: обучение, честная оценка на holdout и рекомендации по промокодам.

Здесь живёт вся логика проекта 1: двухмодельный uplift против transformed outcome,
Qini/AUUC/uplift@10% на отложенной выборке и бизнес-интерпретация в рублях.
"""

from functools import lru_cache

import pandas as pd

from shared import dataset, uplift

TRAIN_SHARE = 0.7
POOL_SIZE = 1500
PAGE = {
    "title": "Uplift Engine",
    "slug": "uplift-engine",
    "eyebrow": "Проект 01 · Uplift-моделирование",
    "lead": "Персонализация промокодов: кому давать скидку, чтобы она действительно "
    "изменила решение о заказе, а не оплатила тех, кто заказал бы и так.",
    "chips": [
        {"name": "Модели", "value": "two-model + transformed outcome"},
        {"name": "Метрики", "value": "Qini, AUUC, uplift@10%"},
        {"name": "Стек", "value": "Python, scikit-learn, FastAPI"},
    ],
}


def shuffled(n: int = 6000, seed: int = 7) -> pd.DataFrame:
    """Перемешивает синтетический промо-датасет фиксированным seed."""
    return (
        dataset.make_promo_dataset(n, seed=seed)
        .sample(frac=1.0, random_state=seed)
        .reset_index(drop=True)
    )


def cut_split(data: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Делит перемешанные данные по границе train."""
    edge = int(len(data) * TRAIN_SHARE)
    return data.iloc[:edge], data.iloc[edge:]


def make_split(n: int = 6000, seed: int = 7) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Делит данные на train и holdout без утечки отклика."""
    return cut_split(shuffled(n, seed))


def fit_bundle(train: pd.DataFrame) -> dict[str, object]:
    """Обучает два подхода к uplift на одном train."""
    return {"two_model": uplift.fit_two_model(train), "transformed": uplift.fit_transformed(train)}


def score_holdout(holdout: pd.DataFrame, models: dict[str, object]) -> dict[str, object]:
    """Скоринги обеих моделей на отложенной выборке."""
    return {
        "two_model": uplift.predict_uplift(models["two_model"], holdout),
        "transformed": uplift.predict_transformed(models["transformed"], holdout),
    }


def auc_row(treated, converted, values) -> dict[str, float]:
    """Две интегральные метрики ранжирования для одного вектора скорингов."""
    return {
        "auuc": uplift.auuc(values, treated, converted),
        "uplift_at_10": uplift.uplift_at_share(values, treated, converted),
    }


def metric_row(holdout: pd.DataFrame, scores: dict[str, object]) -> dict[str, dict[str, float]]:
    """Метрики по каждой модели в одном словаре для API."""
    treated, converted = holdout.treated.to_numpy(), holdout.converted.to_numpy()
    return {name: auc_row(treated, converted, values) for name, values in scores.items()}


def qini_records(holdout: pd.DataFrame, values, points: int = 60) -> dict[str, list[float]]:
    """Кривая Qini в виде двух массивов для фронтенда."""
    curve = uplift.qini_curve(
        values, holdout.treated.to_numpy(), holdout.converted.to_numpy(), points
    )
    return {"share": curve.share.round(4).tolist(), "qini": curve.qini.round(3).tolist()}


def model_bundle(train: pd.DataFrame, holdout: pd.DataFrame) -> dict[str, object]:
    """Модели вместе с их скорингами на holdout."""
    models = fit_bundle(train)
    return {"models": models, "scores": score_holdout(holdout, models)}


def summarize(train: pd.DataFrame, holdout: pd.DataFrame) -> dict[str, object]:
    """Полный отчёт: размеры выборок, метрики и кривые Qini."""
    pack = model_bundle(train, holdout)
    return {
        **pack,
        "train_size": len(train),
        "holdout_size": len(holdout),
        "metrics": metric_row(holdout, pack["scores"]),
        "qini": {name: qini_records(holdout, values) for name, values in pack["scores"].items()},
    }


@lru_cache(maxsize=1)
def bundle() -> dict[str, object]:
    """Кэш дорогого обучения на процесс сервиса."""
    return summarize(*make_split())


def enrich(pool: pd.DataFrame, tau) -> pd.DataFrame:
    """Добавляет uplift и ожидаемую инкрементальную маржу на пользователя."""
    return pool.assign(
        uplift=tau,
        expected_margin=tau
        * (pool.basket_size * pool.margin_rate - pool.delivery_cost - pool.promo_value),
    )


def scored_pool() -> pd.DataFrame:
    """Пул пользователей под скоринг с ожидаемой маржой."""
    pool = dataset.make_scoring_pool(POOL_SIZE)
    return enrich(pool, uplift.predict_uplift(bundle()["models"]["two_model"], pool))


def segment_view() -> list[dict]:
    """Средний uplift и ожидаемая маржа по сегментам клиентов."""
    grouped = (
        scored_pool()
        .groupby("segment", as_index=False)
        .agg(
            users=("uplift", "size"),
            uplift=("uplift", "mean"),
            margin=("expected_margin", "mean"),
        )
    )
    return grouped.sort_values("uplift", ascending=False).round(5).to_dict("records")


def select_columns(frame: pd.DataFrame) -> list[dict]:
    """Оставляет колонки, которые видит бизнес на дашборде."""
    columns = ["user_id", "segment", "city", "promo_value", "uplift", "expected_margin"]
    return frame[columns].round(4).to_dict("records")


def top_users(limit: int = 12) -> list[dict]:
    """Топ пользователей по ожидаемому приросту маржи от промокода."""
    return select_columns(scored_pool().sort_values("expected_margin", ascending=False).head(limit))


def summary(pool_size: int | None = None) -> dict[str, object]:
    """Сводка для дашборда: размеры выборок и метрики обеих моделей."""
    data = bundle()
    return {
        "train_size": data["train_size"],
        "holdout_size": data["holdout_size"],
        "metrics": data["metrics"],
        "pool_size": pool_size or POOL_SIZE,
        "champion": max(data["metrics"], key=lambda name: data["metrics"][name]["auuc"]),
    }


def qini() -> dict[str, dict[str, list[float]]]:
    """Кривые Qini для отрисовки."""
    return bundle()["qini"]
