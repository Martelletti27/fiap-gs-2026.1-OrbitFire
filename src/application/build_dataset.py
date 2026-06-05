"""Caso de uso: join features + labels e split temporal do dataset."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd

from src.application.processed_io import (
    DATASET_PARQUET,
    DATASET_SPLIT_JSON,
    FEATURES_PARQUET,
    LABELS_PARQUET,
    write_parquet,
)
from src.config import Settings, ensure_data_dirs, load_settings
from src.domain.dataset import DEFAULT_TRAIN_RATIO, split_name_for_day, temporal_train_test_split

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DatasetBuildReport:
    """Resumo do dataset consolidado."""

    total_rows: int
    train_rows: int
    test_rows: int
    train_days: int
    test_days: int
    parquet_path: Path
    split_meta_path: Path


def build_dataset(settings: Settings | None = None) -> DatasetBuildReport:
    """Une parquets de features e labels e aplica split temporal por dia."""
    cfg = settings or load_settings()
    ensure_data_dirs(cfg)

    features_path = cfg.processed_dir / FEATURES_PARQUET
    labels_path = cfg.processed_dir / LABELS_PARQUET
    _require_parquet(features_path, "build_features")
    _require_parquet(labels_path, "build_labels")

    features_df = pd.read_parquet(features_path)
    labels_df = pd.read_parquet(labels_path)
    merged = _merge_features_labels(features_df, labels_df)

    if merged.empty:
        raise ValueError("Dataset vazio apos join de features e labels")

    days = [_parse_day(value) for value in merged["day"].unique()]
    temporal = temporal_train_test_split(days, DEFAULT_TRAIN_RATIO)
    merged["split"] = merged["day"].map(
        lambda value: split_name_for_day(_parse_day(value), temporal)
    )

    parquet_path = _export_dataset(cfg.processed_dir, merged)
    split_meta_path = _export_split_meta(cfg.processed_dir, temporal)

    train_rows = int((merged["split"] == "train").sum())
    test_rows = int((merged["split"] == "test").sum())
    logger.info(
        "Dataset: rows=%s train=%s test=%s parquet=%s",
        len(merged),
        train_rows,
        test_rows,
        parquet_path,
    )
    return DatasetBuildReport(
        total_rows=len(merged),
        train_rows=train_rows,
        test_rows=test_rows,
        train_days=len(temporal.train_days),
        test_days=len(temporal.test_days),
        parquet_path=parquet_path,
        split_meta_path=split_meta_path,
    )


def _require_parquet(path: Path, module_name: str) -> None:
    """Garante que parquet de entrada existe."""
    if not path.is_file():
        raise FileNotFoundError(
            f"Arquivo nao encontrado: {path}. "
            f"Execute python -m src.application.{module_name} antes do dataset"
        )


def _merge_features_labels(features_df: pd.DataFrame, labels_df: pd.DataFrame) -> pd.DataFrame:
    """Join interno por cell_id e day."""
    return features_df.merge(labels_df, on=["cell_id", "day"], how="inner")


def _parse_day(value: str | date) -> date:
    """Converte day do parquet para date."""
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def _export_dataset(processed_dir: Path, frame: pd.DataFrame) -> Path:
    """Grava dataset unificado em parquet."""
    return write_parquet(processed_dir, DATASET_PARQUET, frame)


def _export_split_meta(processed_dir: Path, temporal) -> Path:
    """Documenta split temporal em JSON para reproducao."""
    processed_dir.mkdir(parents=True, exist_ok=True)
    path = processed_dir / DATASET_SPLIT_JSON
    payload = {
        "strategy": "temporal",
        "train_ratio": DEFAULT_TRAIN_RATIO,
        "train_days": sorted(day.isoformat() for day in temporal.train_days),
        "test_days": sorted(day.isoformat() for day in temporal.test_days),
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def main() -> None:
    """Entrypoint: python -m src.application.build_dataset"""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    report = build_dataset()
    print(
        f"Dataset: rows={report.total_rows} train={report.train_rows} "
        f"test={report.test_rows} parquet={report.parquet_path} "
        f"split={report.split_meta_path}"
    )


if __name__ == "__main__":
    main()
