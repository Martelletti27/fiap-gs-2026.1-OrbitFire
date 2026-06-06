"""Testes do caso de uso build_dataset (S2.E3)."""

import json
from dataclasses import replace
from pathlib import Path

import pandas as pd
import pytest

from src.application.build_dataset import build_dataset
from src.application.processed_io import (
    DATASET_PARQUET,
    DATASET_SPLIT_JSON,
    FEATURES_PARQUET,
    LABELS_PARQUET,
)
from src.config import load_settings


@pytest.fixture
def dataset_settings(tmp_path: Path):
    """Settings com parquets de entrada em pasta temporaria."""
    base = load_settings(env_file=Path("/arquivo/inexistente.env"))
    processed = tmp_path / "processed"
    processed.mkdir()
    _write_sample_parquets(processed)
    return replace(base, processed_dir=processed)


def _write_sample_parquets(processed_dir: Path) -> None:
    """Cria features e labels minimos para join."""
    features = pd.DataFrame(
        [
            {
                "cell_id": "DF_-15.80_-47.90",
                "day": "2026-06-01",
                "fires_1d": 0,
                "fires_7d": 1,
                "fires_30d": 1,
                "days_without_rain": 2,
                "temp_mean_7d": 30.0,
                "precip_sum_7d": 1.0,
                "wind_mean_7d": 12.0,
                "neighbor_fires_7d": 0,
                "season_month": 6,
            },
            {
                "cell_id": "DF_-15.80_-47.90",
                "day": "2026-06-02",
                "fires_1d": 1,
                "fires_7d": 2,
                "fires_30d": 2,
                "days_without_rain": 3,
                "temp_mean_7d": 31.0,
                "precip_sum_7d": 0.5,
                "wind_mean_7d": 14.0,
                "neighbor_fires_7d": 1,
                "season_month": 6,
            },
            {
                "cell_id": "GO_-16.00_-49.10",
                "day": "2026-06-01",
                "fires_1d": 0,
                "fires_7d": 0,
                "fires_30d": 0,
                "days_without_rain": 1,
                "temp_mean_7d": 28.0,
                "precip_sum_7d": 2.0,
                "wind_mean_7d": 8.0,
                "neighbor_fires_7d": 2,
                "season_month": 6,
            },
        ]
    )
    labels = pd.DataFrame(
        [
            {"cell_id": "DF_-15.80_-47.90", "day": "2026-06-01", "fire_tomorrow": 1},
            {"cell_id": "DF_-15.80_-47.90", "day": "2026-06-02", "fire_tomorrow": 0},
            {"cell_id": "GO_-16.00_-49.10", "day": "2026-06-01", "fire_tomorrow": 0},
        ]
    )
    features.to_parquet(processed_dir / FEATURES_PARQUET, index=False)
    labels.to_parquet(processed_dir / LABELS_PARQUET, index=False)


def test_build_dataset_merges_and_splits(dataset_settings) -> None:
    """Deve unir features/labels e marcar split temporal."""
    report = build_dataset(dataset_settings)

    assert report.total_rows == 3
    assert report.train_rows >= 1
    assert report.test_rows >= 1
    assert report.parquet_path.is_file()
    assert report.split_meta_path.is_file()

    df = pd.read_parquet(report.parquet_path)
    assert "fire_tomorrow" in df.columns
    assert "split" in df.columns
    assert set(df["split"]) <= {"train", "test"}

    meta = json.loads(report.split_meta_path.read_text(encoding="utf-8"))
    assert meta["strategy"] == "temporal"
    assert meta["train_days"]
    assert meta["test_days"]


def test_build_dataset_requires_features(dataset_settings) -> None:
    """Deve falhar se features parquet nao existir."""
    (dataset_settings.processed_dir / FEATURES_PARQUET).unlink()
    with pytest.raises(FileNotFoundError, match="build_features"):
        build_dataset(dataset_settings)


def test_parquet_path_under_processed(dataset_settings) -> None:
    """Dataset deve ficar em data/processed/dataset_cell_day.parquet."""
    report = build_dataset(dataset_settings)
    assert report.parquet_path == dataset_settings.processed_dir / DATASET_PARQUET
    assert report.split_meta_path == dataset_settings.processed_dir / DATASET_SPLIT_JSON
