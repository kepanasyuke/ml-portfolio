"""Бизнес-метрики доставки в терминах вакансии: GMV, CM2, NR, CPO, ROI.

Все функции работают с кадром заказов и возвращают числа в рублях, чтобы
ML-метрики можно было переводить в деньги на одном экране.
"""

import numpy as np
import pandas as pd


def gmv(orders: pd.DataFrame) -> float:
    """Оборот: сумма GMV по заказам."""
    return float(orders["gmv"].sum())


def paid_orders(orders: pd.DataFrame) -> pd.DataFrame:
    """Только оплаченные заказы: доставка и маржа считаются по ним."""
    return orders[orders["converted"] == 1]


def cm2(orders: pd.DataFrame) -> float:
    """Contribution margin 2: маржа после себестоимости и доставки оплаченных заказов."""
    paid = paid_orders(orders)
    return float((paid["gmv"] * paid["margin_rate"] - paid["delivery_cost"]).sum())


def net_revenue(orders: pd.DataFrame) -> float:
    """NR: выручка за вычетом стоимости промокодов."""
    return float(orders["gmv"].sum() - orders["promo_cost"].sum())


def cpo(orders: pd.DataFrame) -> float:
    """Cost per order: стоимость промокодов на один оплаченный заказ."""
    conversions = float(orders["converted"].sum())
    return float(orders["promo_cost"].sum() / conversions) if conversions else 0.0


def roi(orders: pd.DataFrame) -> float:
    """ROI промо-кампании: CM2 на рубль промо-затрат."""
    spend = float(orders["promo_cost"].sum())
    return float(cm2(orders) / spend) if spend else 0.0


def conversion_rate(orders: pd.DataFrame) -> float:
    """Доля заказов от числа получателей."""
    return float(orders["converted"].mean()) if len(orders) else 0.0


def incremental_gmv(treated: pd.DataFrame, control: pd.DataFrame) -> float:
    """Инкрементальный GMV: разница средних между тестом и контролем."""
    return float(treated["gmv"].mean() - control["gmv"].mean())


def incremental_conversion(treated: pd.DataFrame, control: pd.DataFrame) -> float:
    """Инкрементальная конверсия в процентных пунктах."""
    return float(treated["converted"].mean() - control["converted"].mean())


def promo_efficiency(orders: pd.DataFrame) -> pd.DataFrame:
    """Эффективность по номиналам промокода: GMV, CM2 и CPO."""
    grouped = (
        paid_orders(orders.assign(margin=orders.gmv * orders.margin_rate - orders.delivery_cost))
        .groupby("promo_value", as_index=False)
        .agg(
            users=("converted", "size"),
            conversions=("converted", "sum"),
            gmv=("gmv", "sum"),
            promo_cost=("promo_cost", "sum"),
            cm2=("margin", "sum"),
        )
    )
    return grouped.assign(
        conversion_rate=grouped.conversions / grouped.users,
        cpo=grouped.promo_cost / grouped.conversions.replace(0, np.nan),
    )


def summary(orders: pd.DataFrame) -> dict[str, float]:
    """Сводка метрик одним словарём для API и дашборда."""
    return {
        "users": float(len(orders)),
        "gmv": gmv(orders),
        "cm2": cm2(orders),
        "nr": net_revenue(orders),
        "cpo": cpo(orders),
        "roi": roi(orders),
        "conversion": conversion_rate(orders),
    }
