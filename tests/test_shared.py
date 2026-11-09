"""Сквозные тесты общего слоя: данные, метрики и AST-гейт стиля."""

import textwrap
from pathlib import Path

from shared import dataset, metrics, uplift
from tools.style_gate import check_file


def test_dataset_is_deterministic():
    first = dataset.make_promo_dataset(500, seed=42)
    second = dataset.make_promo_dataset(500, seed=42)
    assert first.equals(second)
    assert set(first.treated.unique()) == {0, 1}


def test_business_metrics_non_negative():
    frame = dataset.make_promo_dataset(800, seed=3)
    summary = metrics.summary(frame)
    assert summary["gmv"] > 0
    assert summary["nr"] <= summary["gmv"]
    assert summary["cpo"] > 0


def test_promo_efficiency_has_four_nominals():
    frame = dataset.make_promo_dataset(800, seed=4)
    table = metrics.promo_efficiency(frame)
    assert len(table) == 4
    assert (table.conversion_rate.between(0, 1)).all()


def test_uplift_qini_curve_is_monotonic_in_population():
    frame = dataset.make_promo_dataset(600, seed=5)
    scores = frame.promo_sensitivity.to_numpy()
    curve = uplift.qini_curve(scores, frame.treated.to_numpy(), frame.converted.to_numpy())
    assert curve.share.is_monotonic_increasing
    assert curve.share.iloc[-1] <= 1.0


def test_style_gate_flags_early_return(tmp_path: Path):
    sample = tmp_path / "bad_style.py"
    sample.write_text(
        textwrap.dedent(
            """
            def pick(value):
                if value > 0:
                    return "плюс"
                return "минус"
            """
        ),
        encoding="utf-8",
    )
    problems = check_file(sample)
    assert any("один return" in problem for problem in problems)


def test_style_gate_accepts_clean_function(tmp_path: Path):
    sample = tmp_path / "good_style.py"
    sample.write_text(
        textwrap.dedent(
            """
            def double(value):
                return value * 2
            """
        ),
        encoding="utf-8",
    )
    assert check_file(sample) == []
