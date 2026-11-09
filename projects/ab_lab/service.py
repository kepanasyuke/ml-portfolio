"""A/B-лаборатория: размер выборки, CUPED и always-valid p-value.

В вакансии это пункт «опыт проведения A/B-тестов»: до запуска считаем MDE и срок,
после — сравниваем наивную оценку с CUPED-скорректированной и объясняем,
почему подглядывание в тест ломает обычный p-value.
"""

from functools import lru_cache

import numpy as np
import pandas as pd
from scipy.stats import norm

ALPHA = 0.05
POWER = 0.8
TRAFFIC = 1200
MDE = 0.04
SIGMA = 700.0
BASE_MEAN = 1800.0
PAGE = {
    "title": "A/B Lab",
    "slug": "ab-lab",
    "eyebrow": "Проект 03 · A/B-тесты",
    "lead": "Дизайн и разбор эксперимента: сколько трафика нужно, чтобы увидеть эффект, "
    "как CUPED срезает дисперсию и почему нельзя подглядывать в тест обычным p-value.",
    "chips": [
        {"name": "Дизайн", "value": "MDE, power, длительность"},
        {"name": "Анализ", "value": "Welch, CUPED, mSPRT"},
        {"name": "Стек", "value": "Python, numpy, scipy, FastAPI"},
    ],
}


def build_frame(gen: np.random.Generator, pre: np.ndarray, effect: float) -> pd.DataFrame:
    """Назначает группы и добавляет эффект к post-периоду."""
    group = gen.integers(0, 2, len(pre))
    return pd.DataFrame(
        {
            "group": group,
            "pre": pre,
            "post": pre + gen.normal(0.0, SIGMA, len(pre)) + group * effect,
        }
    )


def draw_experiment(gen: np.random.Generator, n: int, effect: float) -> pd.DataFrame:
    """Собирает pre/post-периоды и group-флаг с заданным эффектом."""
    pre = gen.normal(BASE_MEAN, 600.0, n)
    return build_frame(gen, pre, effect)


def experiment(n: int = 8000, effect: float = 60.0, seed: int = 5) -> pd.DataFrame:
    """Синтетический A/B: pre-период и post-период в рублях на пользователя."""
    return draw_experiment(np.random.default_rng(seed), n, effect)


@lru_cache(maxsize=1)
def data() -> pd.DataFrame:
    """Экспериментальные данные, сгенерированные один раз на процесс."""
    return experiment()


def sample_size(
    mean: float, sigma: float, mde_rel: float, alpha: float = ALPHA, power: float = POWER
) -> int:
    """Размер одной группы для двустороннего теста среднего."""
    delta = mean * mde_rel
    return int(np.ceil(2 * ((norm.ppf(1 - alpha / 2) + norm.ppf(power)) * sigma / delta) ** 2))


def duration(sample_per_arm: int, traffic: int = TRAFFIC) -> int:
    """Сколько дней копить трафик при заданном потоке пользователей в день."""
    return int(np.ceil(2 * sample_per_arm / traffic))


def standard_error(left: pd.Series, right: pd.Series) -> float:
    """Стандартная ошибка разницы средних по Уэлчу."""
    return float(np.sqrt(left.var(ddof=1) / len(left) + right.var(ddof=1) / len(right)))


def normal_p(diff: float, se: float) -> float:
    """Двусторонний p-value нормальной аппроксимации."""
    return float(2 * (1 - norm.cdf(abs(diff / se))))


def welch(left: pd.Series, right: pd.Series) -> dict[str, float]:
    """Разница средних, стандартная ошибка и p-value по Уэлчу."""
    diff = float(right.mean() - left.mean())
    return {
        "diff": diff,
        "se": standard_error(left, right),
        "p_value": normal_p(diff, standard_error(left, right)),
    }


def theta(pre: np.ndarray, post: np.ndarray) -> float:
    """Коэффициент CUPED: ковариация pre и post, нормированная на дисперсию pre."""
    return float(np.cov(pre, post, ddof=1)[0, 1] / np.var(pre, ddof=1))


def adjusted(post: np.ndarray, pre: np.ndarray, coefficient: float) -> np.ndarray:
    """Метрика, очищенная от предпериодных различий групп."""
    return post - coefficient * (pre - pre.mean())


def pooled_theta(control: pd.DataFrame, test: pd.DataFrame) -> float:
    """Единый коэффициент CUPED, посчитанный на объединённой выборке."""
    return theta(
        np.concatenate([control.pre.to_numpy(), test.pre.to_numpy()]),
        np.concatenate([control.post.to_numpy(), test.post.to_numpy()]),
    )


def reduction_value(post: np.ndarray, pre: np.ndarray, coefficient: float) -> float:
    """Доля срезанной дисперсии после CUPED-корректировки."""
    return float(1 - np.var(adjusted(post, pre, coefficient), ddof=1) / np.var(post, ddof=1))


def variance_reduction(control: pd.DataFrame, test: pd.DataFrame, coefficient: float) -> float:
    """Сокращение дисперсии на объединённых данных эксперимента."""
    return reduction_value(
        np.concatenate([control.post.to_numpy(), test.post.to_numpy()]),
        np.concatenate([control.pre.to_numpy(), test.pre.to_numpy()]),
        coefficient,
    )


def sequential_p(diff: float, se: float, looks: int = 4, tau: float = 3.0) -> float:
    """Always-valid p-value по mSPRT для нескольких промежуточных взглядов."""
    z = diff / se
    return float(min(1.0, np.sqrt(1 + looks / tau) * np.exp(-looks * z * z / (2 * (looks + tau)))))


def split(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Делит эксперимент на контроль и тест."""
    return frame[frame.group == 0], frame[frame.group == 1]


def naive_block(control: pd.DataFrame, test: pd.DataFrame) -> dict[str, float]:
    """Наивная оценка эффекта плюс последовательный p-value."""
    stats = welch(control.post, test.post)
    return {**stats, "sequential_p": sequential_p(stats["diff"], stats["se"])}


def corrected_welch(
    control: pd.DataFrame, test: pd.DataFrame, coefficient: float
) -> dict[str, float]:
    """Сравнение групп после CUPED-корректировки метрики."""
    return welch(
        adjusted(control.post.to_numpy(), control.pre.to_numpy(), coefficient),
        adjusted(test.post.to_numpy(), test.pre.to_numpy(), coefficient),
    )


def cuped_result(control: pd.DataFrame, test: pd.DataFrame) -> dict[str, float]:
    """Эффект после CUPED-корректировки и коэффициент theta."""
    coefficient = pooled_theta(control, test)
    return {**corrected_welch(control, test, coefficient), "theta": round(coefficient, 3)}


def assemble(control: pd.DataFrame, test: pd.DataFrame) -> dict[str, object]:
    """Собирает отчёт по эксперименту из блоков."""
    coefficient = pooled_theta(control, test)
    return {
        "naive": naive_block(control, test),
        "cuped": cuped_result(control, test),
        "reduction": variance_reduction(control, test, coefficient),
        "counts": {"control": len(control), "test": len(test)},
        "means": {
            "control": round(float(control.post.mean()), 2),
            "test": round(float(test.post.mean()), 2),
        },
    }


def report(frame: pd.DataFrame) -> dict[str, object]:
    """Отчёт по эксперименту: наивная и CUPED-оценки эффекта."""
    return assemble(*split(frame))


def design(mde_rel: float = MDE, traffic: int = TRAFFIC) -> dict[str, float]:
    """Расчёт размера выборки и длительности теста под заданный MDE."""
    size = sample_size(BASE_MEAN, SIGMA, mde_rel)
    return {
        "mde_rel": mde_rel,
        "mde_abs": round(BASE_MEAN * mde_rel, 2),
        "sample_per_arm": size,
        "total": 2 * size,
        "days": duration(size, traffic),
        "traffic": traffic,
        "sigma": SIGMA,
        "alpha": ALPHA,
        "power": POWER,
    }
