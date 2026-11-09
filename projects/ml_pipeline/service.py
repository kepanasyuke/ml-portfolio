"""Пайплайн обучения uplift-модели в стиле DVC: стадии, хеши, кэш и локальный S3.

В вакансии это «строить и поддерживать пайплайны обучения и скоринга» плюс Trino/S3/DVC.
Здесь S3 эмулируется каталогом .local_s3, а каждая стадия описывается хешем входов:
если ничего не изменилось, стадия берётся из кэша и не пересчитывается.
"""

import hashlib
import json
import time
from functools import reduce
from pathlib import Path

import joblib
import pandas as pd

from shared import dataset, uplift

BUCKET = Path(__file__).resolve().parents[2] / ".local_s3"
DATA_KEY = "data/promo.csv"
MODEL_KEY = "models/uplift.joblib"
METRICS_KEY = "metrics/eval.json"
MANIFEST_KEY = "manifest.json"
STAGES = ("extract", "validate", "train", "evaluate")
PAGE = {
    "title": "ML Pipeline",
    "slug": "ml-pipeline",
    "eyebrow": "Проект 04 · Пайплайны",
    "lead": "Стадии обучения и скоринга с контентными хешами: изменённые данные пересчитываются, "
    "неизменные берутся из кэша. Артефакты лежат в локальном S3-хранилище.",
    "chips": [
        {"name": "Стадии", "value": "extract → validate → train → evaluate"},
        {"name": "Кэш", "value": "sha256 по входам и параметрам"},
        {"name": "Стек", "value": "Python, joblib, pandas, FastAPI"},
    ],
}


def bucket_path(key: str) -> Path:
    """Путь объекта в локальном бакете."""
    return BUCKET / key


def make_parent(path: Path) -> Path:
    """Создаёт каталог под объект и возвращает путь."""
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def ensure(key: str) -> Path:
    """Путь объекта в бакете с готовым родительским каталогом."""
    return make_parent(bucket_path(key))


def write_bytes(key: str, payload: bytes) -> str:
    """Кладёт объект в бакет и возвращает его ключ."""
    ensure(key).write_bytes(payload)
    return key


def stage_hash(inputs: list[Path], params: dict) -> str:
    """sha256 по содержимому входов и параметрам стадии."""
    payload = b"".join(path.read_bytes() for path in inputs) + json.dumps(
        params, sort_keys=True
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:12]


def manifest() -> dict:
    """Последний манифест пайплайна либо пустой словарь."""
    path = bucket_path(MANIFEST_KEY)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def is_cached(name: str, hash_value: str) -> bool:
    """Проверяет, совпадает ли хеш стадии с прошлым запуском."""
    return manifest().get("hashes", {}).get(name) == hash_value


def cached_record(name: str, hash_value: str) -> dict:
    """Запись о стадии, взятой из кэша."""
    return {"name": name, "hash": hash_value, "status": "cached", "duration": 0.0, "result": {}}


def finish(name: str, hash_value: str, action, started: float) -> dict:
    """Выполняет действие стадии и собирает запись для манифеста."""
    payload = action()
    return {
        "name": name,
        "hash": hash_value,
        "status": "ran",
        "duration": round(time.perf_counter() - started, 3),
        **payload,
    }


def perform(name: str, hash_value: str, action) -> dict:
    """Запускает стадию с замером времени."""
    started = time.perf_counter()
    return finish(name, hash_value, action, started)


def execute(name: str, hash_value: str, force: bool, action) -> dict:
    """Кэш или пересчёт: решение принимается по хешу стадии."""
    return (
        cached_record(name, hash_value)
        if is_cached(name, hash_value) and not force
        else perform(name, hash_value, action)
    )


def stage(name: str, inputs: list[str], params: dict, force: bool, action) -> dict:
    """Обёртка стадии: хеш по входам и параметрам, затем выполнение."""
    hash_value = stage_hash([bucket_path(key) for key in inputs], params)
    return execute(name, hash_value, force, action)


def write_frame(key: str, frame: pd.DataFrame) -> str:
    """Сохраняет датасет в бакет как CSV."""
    frame.to_csv(ensure(key), index=False)
    return key


def build_dataset_file() -> dict:
    """Стадия extract: синтетика промо-эксперимента в локальный S3."""
    frame = dataset.make_promo_dataset(4000, seed=17)
    return {
        "output": write_frame(DATA_KEY, frame),
        "result": {"rows": len(frame), "treated_share": round(float(frame.treated.mean()), 3)},
    }


def checks_of(frame: pd.DataFrame) -> dict:
    """Контракт качества данных: пропуски, доля конверсий, номиналы."""
    return {
        "rows": len(frame),
        "nulls": int(frame.isna().sum().sum()),
        "conversion_rate": round(float(frame.converted.mean()), 3),
        "promo_values": sorted(int(value) for value in frame.promo_value.unique()),
    }


def passed(frame: pd.DataFrame) -> bool:
    """Проверяет, что датасет годится для обучения."""
    checks = checks_of(frame)
    return bool(checks["nulls"] == 0 and 0.01 < checks["conversion_rate"] < 0.9)


def validate_file() -> dict:
    """Стадия validate: читает датасет и проверяет контракт."""
    frame = pd.read_csv(bucket_path(DATA_KEY))
    return {"output": DATA_KEY, "result": {"checks": checks_of(frame), "passed": passed(frame)}}


def dump_model(pair) -> str:
    """Сохраняет пару uplift-моделей в бакет."""
    joblib.dump(pair, ensure(MODEL_KEY))
    return MODEL_KEY


def build_model() -> dict:
    """Стадия train: обучение двухмодельного uplift на данных из бакета."""
    frame = pd.read_csv(bucket_path(DATA_KEY))
    return {"output": dump_model(uplift.fit_two_model(frame)), "result": {"rows": len(frame)}}


def load_inputs() -> tuple[pd.DataFrame, object]:
    """Читает датасет и модель из бакета."""
    return pd.read_csv(bucket_path(DATA_KEY)), joblib.load(bucket_path(MODEL_KEY))


def save_metrics(metrics: dict) -> dict:
    """Пишет метрики стадии evaluate в бакет."""
    write_bytes(METRICS_KEY, json.dumps(metrics, ensure_ascii=False).encode("utf-8"))
    return metrics


def metrics_of(frame: pd.DataFrame, scores) -> dict:
    """Метрики качества ранжирования для артефакта."""
    metrics = {
        "auuc": round(
            float(uplift.auuc(scores, frame.treated.to_numpy(), frame.converted.to_numpy())), 3
        ),
        "uplift_at_10": round(
            float(
                uplift.uplift_at_share(scores, frame.treated.to_numpy(), frame.converted.to_numpy())
            ),
            4,
        ),
        "rows": len(frame),
    }
    return save_metrics(metrics)


def evaluate_model() -> dict:
    """Стадия evaluate: скоринг датасета сохранённой моделью и запись метрик."""
    frame, pair = load_inputs()
    return {"output": METRICS_KEY, "result": metrics_of(frame, uplift.predict_uplift(pair, frame))}


def run_extract(state: dict, force: bool) -> dict:
    """Стадия extract в оркестраторе: добавляет датасет в состояние."""
    record = stage("extract", [], {"stage": "extract", "rows": 4000}, force, build_dataset_file)
    return {**state, "records": [*state["records"], record], "data": DATA_KEY}


def run_validate(state: dict, force: bool) -> dict:
    """Стадия validate: зависит от датасета."""
    record = stage("validate", [state["data"]], {"stage": "validate"}, force, validate_file)
    return {**state, "records": [*state["records"], record]}


def run_train(state: dict, force: bool) -> dict:
    """Стадия train: зависит от датасета, пишет модель в бакет."""
    record = stage(
        "train", [state["data"]], {"stage": "train", "model": "hist-gb"}, force, build_model
    )
    return {**state, "records": [*state["records"], record], "model": MODEL_KEY}


def run_evaluate(state: dict, force: bool) -> dict:
    """Стадия evaluate: зависит от датасета и модели."""
    record = stage(
        "evaluate", [state["data"], state["model"]], {"stage": "evaluate"}, force, evaluate_model
    )
    return {**state, "records": [*state["records"], record], "metrics": record["result"]}


RUNNERS = {
    "extract": run_extract,
    "validate": run_validate,
    "train": run_train,
    "evaluate": run_evaluate,
}
INITIAL = {"records": [], "data": DATA_KEY, "model": MODEL_KEY, "metrics": {}}


def pipeline(force: bool = False) -> dict:
    """Прогоняет стадии по порядку, накапливая состояние."""
    return reduce(lambda state, name: RUNNERS[name](state, force), STAGES, INITIAL)


def hashes_of(state: dict) -> dict[str, str]:
    """Хеши стадий для манифеста."""
    return {record["name"]: record["hash"] for record in state["records"]}


def encoded_manifest(state: dict) -> bytes:
    """Сериализует стадии и хеши в JSON-байты."""
    payload = {"hashes": hashes_of(state), "stages": state["records"]}
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


def write_manifest(state: dict) -> str:
    """Сохраняет манифест со стадиями и хешами в бакет."""
    return write_bytes(MANIFEST_KEY, encoded_manifest(state))


def save_manifest(state: dict) -> dict[str, str]:
    """Пишет манифест с хешами стадий и возвращает их."""
    write_manifest(state)
    return hashes_of(state)


def persist(state: dict) -> dict:
    """Отдаёт отчёт для дашборда, сохраняя манифест."""
    return {
        "stages": state["records"],
        "metrics": state["metrics"],
        "bucket": str(BUCKET),
        "hashes": save_manifest(state),
    }


def run(force: bool = False) -> dict:
    """Полный прогон пайплайна с сохранением манифеста."""
    result = pipeline(force)
    return persist(result)


def artifacts() -> list[dict]:
    """Объекты локального S3-бакета с размерами."""
    files = [
        {"key": path.relative_to(BUCKET).as_posix(), "bytes": path.stat().st_size}
        for path in BUCKET.rglob("*")
        if path.is_file()
    ]
    return sorted(files, key=lambda item: item["key"])


def state() -> dict:
    """Текущее состояние пайплайна для страницы дашборда."""
    saved = manifest()
    return {"stages": saved.get("stages", []), "artifacts": artifacts(), "bucket": str(BUCKET)}
