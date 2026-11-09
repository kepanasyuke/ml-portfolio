"""Синтетика доставки Магнит: клиентская база, промо-дизайн и наблюдаемый отклик.

Схема повторяет то, с чем работает команда OMNI: пользователь, назначение промокода,
конверсия в заказ и GMV. Данные генерируются детерминированно по seed, поэтому
результаты моделей и тестов воспроизводимы без доступа к продовому S3.
"""

import numpy as np
import pandas as pd

SEGMENTS = ("new", "loyal", "sleeping", "vip", "builder")
CITIES = ("Москва", "Санкт-Петербург", "Краснодар", "Казань", "Екатеринбург")
PROMO_VALUES = (100, 200, 300, 500)
PROMO_MIX = (0.40, 0.30, 0.20, 0.10)
SEGMENT_UPLIFT = {"new": 0.10, "loyal": 0.03, "sleeping": 0.14, "vip": 0.02, "builder": 0.07}


def sigmoid(x: np.ndarray | float) -> np.ndarray:
    """Логистическая функция без переполнения на больших значениях."""
    return 1.0 / (1.0 + np.exp(-np.clip(np.asarray(x, dtype=float), -30.0, 30.0)))


def draw_orders(gen: np.random.Generator, n: int) -> np.ndarray:
    """Число заказов за 30 дней: пуассоновский спрос с потолком."""
    return np.clip(gen.poisson(3.4, n), 0, 24)


def assemble_users(gen: np.random.Generator, n: int, orders: np.ndarray) -> pd.DataFrame:
    """Собирает профиль клиента из независимых розыгрышей."""
    return pd.DataFrame(
        {
            "user_id": np.arange(1, n + 1),
            "segment": gen.choice(SEGMENTS, n, p=(0.22, 0.34, 0.20, 0.10, 0.14)),
            "city": gen.choice(CITIES, n, p=(0.42, 0.20, 0.14, 0.13, 0.11)),
            "age": np.clip(gen.normal(36, 11, n), 18, 75).round(0),
            "orders_30d": orders,
            "gmv_30d": (orders * gen.normal(2100, 420, n)).round(0),
            "days_since_order": gen.integers(1, 95, n),
            "basket_size": np.clip(gen.normal(2400, 700, n), 500, 7000).round(0),
            "margin_rate": np.clip(gen.normal(0.26, 0.05, n), 0.10, 0.42).round(3),
            "delivery_cost": np.clip(gen.normal(190, 35, n), 90, 320).round(0),
            "app_installed": (gen.random(n) < 0.61).astype(int),
            "promo_sensitivity": np.clip(gen.beta(2.2, 3.0, n), 0.01, 0.98).round(3),
        }
    )


def make_users(n: int = 4000, rng: np.random.Generator | None = None) -> pd.DataFrame:
    """Профиль клиента доставки: RFM, сегмент, город и чувствительность к промо."""
    gen = rng if rng is not None else np.random.default_rng(7)
    return assemble_users(gen, n, draw_orders(gen, n))


def base_propensity(users: pd.DataFrame) -> np.ndarray:
    """Вероятность заказа без промокода."""
    return sigmoid(
        -2.05
        + 0.26 * users.orders_30d
        - 0.016 * users.days_since_order
        + 0.15 * users.app_installed
    )


def uplift_signal(users: pd.DataFrame, promo: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Прирост вероятности заказа от промокода: сегмент x номинал x шум."""
    raw = (
        users.segment.map(SEGMENT_UPLIFT).to_numpy()
        * (promo / 300.0)
        * (0.8 + 0.4 * users.promo_sensitivity)
    )
    return np.clip(raw + rng.normal(0.0, 0.04, len(users)), 0.0, 0.35)


def draw_design(users: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Случайное назначение промокода: treated-флаг и номинал."""
    treated = rng.integers(0, 2, len(users))
    return pd.DataFrame(
        {"treated": treated, "promo_value": rng.choice(PROMO_VALUES, len(users), p=PROMO_MIX)}
    )


def order_probability(
    users: pd.DataFrame, design: pd.DataFrame, rng: np.random.Generator
) -> np.ndarray:
    """Итоговая вероятность заказа: базовая плюс эффект промокода."""
    tau = np.where(
        design.treated == 1, uplift_signal(users, design.promo_value.to_numpy(), rng), 0.0
    )
    return np.clip(base_propensity(users) + tau, 0.001, 0.999)


def observe(
    users: pd.DataFrame, design: pd.DataFrame, rng: np.random.Generator
) -> tuple[np.ndarray, np.ndarray]:
    """Наблюдаемые конверсия в заказ и GMV с учётом эффекта промокода."""
    converted = (rng.random(len(users)) < order_probability(users, design, rng)).astype(int)
    return converted, np.where(
        converted == 1, users.basket_size * rng.normal(1.0, 0.18, len(users)), 0.0
    )


def outcomes_frame(
    users: pd.DataFrame, design: pd.DataFrame, rng: np.random.Generator
) -> pd.DataFrame:
    """Кадр наблюдаемого отклика: конверсия, GMV и стоимость промокода."""
    converted, gmv = observe(users, design, rng)
    return pd.DataFrame(
        {"converted": converted, "gmv": gmv.round(0), "promo_cost": design.promo_value * converted}
    )


def build_dataset(users: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Склеивает профиль, дизайн эксперимента и отклик."""
    design = draw_design(users, rng)
    return pd.concat(
        [users.reset_index(drop=True), design, outcomes_frame(users, design, rng)], axis=1
    )


def make_promo_dataset(n: int = 4000, seed: int = 7) -> pd.DataFrame:
    """Готовый датасет промо-эксперимента для обучения uplift-моделей."""
    rng = np.random.default_rng(seed)
    return build_dataset(make_users(n, rng), rng)


def draw_promo(users: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Назначает номинал будущей акции в пуле скоринга."""
    return users.assign(promo_value=rng.choice(PROMO_VALUES, len(users), p=PROMO_MIX))


def make_scoring_pool(n: int = 1500, seed: int = 21) -> pd.DataFrame:
    """Пул пользователей под скоринг: без отклика, с номиналом будущей акции."""
    rng = np.random.default_rng(seed)
    return draw_promo(make_users(n, rng), rng)
