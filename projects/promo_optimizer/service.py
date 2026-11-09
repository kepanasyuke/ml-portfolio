"""Оптимизатор промокодов: выбор номинала и получателей под бюджет, CPO и маржу.

Логика повторяет задачу из вакансии: uplift-скоринг даёт ожидаемый прирост конверсии,
а оптимизатор раскладывает ограниченный бюджет так, чтобы максимизировать
инкрементальную CM2 при CPO не выше заданного.
"""

from functools import lru_cache

import numpy as np
import pandas as pd

from shared import dataset, uplift

POOL_SIZE = 1200
BUDGET = 90_000.0
CPO_CAP = 220.0
PROMOS = dataset.PROMO_VALUES
PAGE = {
    "title": "Promo Optimizer",
    "slug": "promo-optimizer",
    "eyebrow": "Проект 02 · Промо-экономика",
    "lead": "Сколько и кому давать скидку: оптимизатор собирает план рассылки под бюджет, "
    "потолок CPO и требования к марже, а не «всем по 300 рублей».",
    "chips": [
        {"name": "Ограничения", "value": "бюджет, CPO, CM2"},
        {"name": "Метод", "value": "greedy по эффективности + guard по CPO"},
        {"name": "Стек", "value": "Python, pandas, FastAPI"},
    ],
}


@lru_cache(maxsize=1)
def trained():
    """Модель отклика, обученная на промо-эксперименте."""
    return uplift.fit_two_model(dataset.make_promo_dataset(5000, seed=11))


def pool_frame() -> pd.DataFrame:
    """Пул клиентов с базовой вероятностью заказа без скидки."""
    pool = dataset.make_scoring_pool(POOL_SIZE, seed=33)
    return pool.assign(base=dataset.base_propensity(pool))


def tau_matrix(frame: pd.DataFrame) -> pd.DataFrame:
    """Uplift для каждого номинала промокода."""
    return pd.DataFrame(
        {
            value: uplift.predict_uplift(trained(), frame.assign(promo_value=value))
            for value in PROMOS
        }
    )


def candidates(frame: pd.DataFrame) -> pd.DataFrame:
    """Все варианты «пользователь × номинал» с uplift-скорингом."""
    taus = tau_matrix(frame)
    return pd.DataFrame(
        [
            {
                "user_id": user_id,
                "segment": segment,
                "promo": value,
                "tau": max(float(taus.at[index, value]), 0.0),
                "basket": basket,
                "margin_rate": rate,
                "delivery_cost": delivery,
                "base": base,
            }
            for index, (user_id, segment, basket, rate, delivery, base) in enumerate(
                zip(
                    frame.user_id,
                    frame.segment,
                    frame.basket_size,
                    frame.margin_rate,
                    frame.delivery_cost,
                    frame.base,
                    strict=False,
                )
            )
            for value in PROMOS
        ]
    )


def margin_of(frame: pd.DataFrame, spend: pd.Series) -> pd.Series:
    """Инкрементальная маржа варианта за вычетом ожидаемых затрат на промокод."""
    return frame.tau * (frame.basket * frame.margin_rate - frame.delivery_cost) - spend


def price(frame: pd.DataFrame) -> pd.DataFrame:
    """Экономика варианта: ожидаемые затраты, инкрементальные GMV и CM2."""
    spend = frame.promo * np.clip(frame.base + frame.tau, 0.001, 1.0)
    return frame.assign(
        exp_spend=spend,
        exp_gmv=frame.tau * frame.basket,
        exp_cm2=margin_of(frame, spend),
        efficiency=margin_of(frame, spend) / np.maximum(spend, 1.0),
    )


@lru_cache(maxsize=1)
def candidate_frame() -> pd.DataFrame:
    """Готовая таблица вариантов: считается один раз на процесс."""
    return price(candidates(pool_frame()))


def take_count(spend: np.ndarray, conversions: np.ndarray, budget: float, cpo_cap: float) -> int:
    """Длина префикса ранжирования, где бюджет и CPO ещё соблюдаются."""
    ok = np.cumsum(spend) <= np.minimum(budget, cpo_cap * np.maximum(np.cumsum(conversions), 1e-9))
    return int(len(ok) if ok.all() else np.argmin(ok))


def rank_options(options: pd.DataFrame) -> pd.DataFrame:
    """Ранжирует варианты по эффективности и оставляет лучший на пользователя."""
    ordered = (
        options[options.efficiency > 0]
        .sort_values("efficiency", ascending=False)
        .reset_index(drop=True)
    )
    return ordered.drop_duplicates("user_id")


def take_prefix(ordered: pd.DataFrame, budget: float, cpo_cap: float) -> pd.DataFrame:
    """Отрезает префикс ранжирования, где ограничения ещё соблюдаются."""
    return ordered.iloc[
        : take_count(ordered.exp_spend.to_numpy(), ordered.tau.to_numpy(), budget, cpo_cap)
    ]


def select(options: pd.DataFrame, budget: float, cpo_cap: float) -> pd.DataFrame:
    """Жадный выбор варианта на пользователя по убыванию эффективности."""
    return take_prefix(rank_options(options), budget, cpo_cap)


def blanket(options: pd.DataFrame, promo: int = 300) -> pd.DataFrame:
    """Базовый сценарий: один и тот же промокод всем клиентам."""
    return options[options.promo == promo]


def summarize_plan(plan: pd.DataFrame) -> dict[str, float]:
    """Экономика плана в терминах GMV, CM2, CPO и ROI."""
    spend = float(plan.exp_spend.sum())
    return {
        "users": len(plan),
        "spend": round(spend, 2),
        "incremental_orders": round(float(plan.tau.sum()), 2),
        "incremental_gmv": round(float(plan.exp_gmv.sum()), 2),
        "incremental_cm2": round(float(plan.exp_cm2.sum()), 2),
        "cpo": round(spend / max(float(plan.tau.sum()), 1e-9), 2),
        "roi": round(float(plan.exp_cm2.sum()) / max(spend, 1e-9), 3),
    }


def promo_mix(plan: pd.DataFrame) -> list[dict]:
    """Разбивка выбранного плана по номиналам промокода."""
    grouped = plan.groupby("promo", as_index=False).agg(
        users=("user_id", "size"),
        spend=("exp_spend", "sum"),
        incremental_cm2=("exp_cm2", "sum"),
    )
    return grouped.round(2).to_dict("records")


def top_rows(plan: pd.DataFrame, limit: int = 10) -> list[dict]:
    """Самые маржинальные строки плана для таблицы на дашборде."""
    columns = ["user_id", "segment", "promo", "tau", "exp_cm2", "efficiency"]
    return (
        plan.sort_values("exp_cm2", ascending=False)
        .head(limit)[columns]
        .round(4)
        .to_dict("records")
    )


def report(plan: pd.DataFrame, baseline: pd.DataFrame) -> dict[str, object]:
    """Сравнение оптимизированного плана с «всем по 300»."""
    return {
        "plan": summarize_plan(plan),
        "blanket": summarize_plan(baseline),
        "by_promo": promo_mix(plan),
        "top": top_rows(plan),
    }


def optimize(budget: float = BUDGET, cpo_cap: float = CPO_CAP) -> dict[str, object]:
    """План распределения при заданных бюджете и потолке CPO."""
    return report(select(candidate_frame(), budget, cpo_cap), blanket(candidate_frame()))


def limits() -> dict[str, float]:
    """Ограничения и число кандидатов для формы на дашборде."""
    return {
        "budget": BUDGET,
        "cpo_cap": CPO_CAP,
        "candidates": len(candidate_frame()),
        "users": int(candidate_frame().user_id.nunique()),
    }
