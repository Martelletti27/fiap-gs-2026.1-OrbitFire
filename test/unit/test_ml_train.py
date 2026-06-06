"""Testes do treino LightGBM (S3.E1)."""

import json
import pickle
from dataclasses import replace
from pathlib import Path

import pandas as pd
import pytest

from src.application.processed_io import DATASET_PARQUET
from src.config import load_settings
from src.infrastructure.ml.confusion_plot import CONFUSION_MATRIX_FILENAME
from src.infrastructure.ml.train import (
    FEATURE_COLUMNS,
    METRICS_FILENAME,
    MODEL_FILENAME,
    TARGET_COLUMN,
    extract_xy,
    train_model,
)


@pytest.fixture
def train_settings(tmp_path: Path):
    """Settings com dataset sintetico em pasta temporaria."""
    base = load_settings(env_file=Path("/arquivo/inexistente.env"))
    processed = tmp_path / "processed"
    models = tmp_path / "models"
    processed.mkdir()
    models.mkdir()
    _write_sample_dataset(processed)
    return replace(
        base,
        processed_dir=processed,
        models_dir=models,
    )


def _write_sample_dataset(processed_dir: Path) -> None:
    """Dataset minimo com variacao para treino e teste."""
    rows = []
    for day, split in [("2026-06-01", "train"), ("2026-06-02", "train"), ("2026-06-03", "test")]:
        for idx, cell in enumerate(["DF_-15.80_-47.90", "GO_-16.00_-49.10"]):
            label = 1 if idx == 0 and day in {"2026-06-02", "2026-06-03"} else 0
            rows.append(
                {
                    "cell_id": cell,
                    "day": day,
                    "fires_1d": idx,
                    "fires_7d": idx + 1,
                    "fires_30d": idx + 2,
                    "days_without_rain": idx,
                    "temp_mean_7d": 30.0 + idx,
                    "precip_sum_7d": 1.0 + idx,
                    "wind_mean_7d": 10.0 + idx,
                    "neighbor_fires_7d": idx + 3,
                    "season_month": 6,
                    "fire_tomorrow": label,
                    "split": split,
                }
            )
    pd.DataFrame(rows).to_parquet(processed_dir / DATASET_PARQUET, index=False)


def test_extract_xy_returns_feature_columns(train_settings) -> None:
    """Deve expor somente colunas de feature acordadas em S2."""
    frame = pd.read_parquet(train_settings.processed_dir / DATASET_PARQUET)
    x_frame, y_series = extract_xy(frame)

    assert list(x_frame.columns) == list(FEATURE_COLUMNS)
    assert y_series.name == TARGET_COLUMN


def test_train_model_saves_artifacts(train_settings) -> None:
    """Deve treinar, salvar pkl, metrics.json e matriz de confusao."""
    report = train_model(train_settings)

    assert report.train_rows == 4
    assert report.test_rows == 2
    assert report.model_path == train_settings.models_dir / MODEL_FILENAME
    assert report.metrics_path == train_settings.models_dir / METRICS_FILENAME
    assert report.confusion_matrix_path == train_settings.models_dir / CONFUSION_MATRIX_FILENAME
    assert report.model_path.is_file()
    assert report.metrics_path.is_file()
    assert report.confusion_matrix_path.is_file()
    assert report.confusion_matrix_path.stat().st_size > 0

    with report.model_path.open("rb") as handle:
        model = pickle.load(handle)
    assert hasattr(model, "predict_proba")

    metrics = json.loads(report.metrics_path.read_text(encoding="utf-8"))
    assert metrics["model"] == "lightgbm"
    assert metrics["feature_columns"] == list(FEATURE_COLUMNS)
    assert "roc_auc" in metrics
    assert "confusion" in metrics
    assert "lgbm_params" in metrics
    assert metrics["tuning_candidates"] >= 1


def test_train_model_requires_dataset(train_settings) -> None:
    """Deve falhar se parquet do dataset nao existir."""
    (train_settings.processed_dir / DATASET_PARQUET).unlink()
    with pytest.raises(FileNotFoundError, match="build_dataset"):
        train_model(train_settings)


def test_train_model_requires_both_splits(train_settings) -> None:
    """Deve falhar se split tiver apenas train ou test."""
    path = train_settings.processed_dir / DATASET_PARQUET
    frame = pd.read_parquet(path)
    frame["split"] = "train"
    frame.to_parquet(path, index=False)

    with pytest.raises(ValueError, match="train e test"):
        train_model(train_settings)
