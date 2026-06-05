"""Caso de uso: engenharia de features por celula e dia."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from src.application.db_loaders import load_cell_day_context
from src.application.processed_io import FEATURES_PARQUET, write_parquet
from src.config import Settings, ensure_data_dirs, load_settings
from src.domain.features import CellDayFeatures, build_features_table
from src.infrastructure.db.repository import repository_session

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FeaturesBuildReport:
    """Resumo da geracao de features."""

    total_rows: int
    cell_count: int
    day_count: int
    parquet_path: Path


def build_features(settings: Settings | None = None) -> FeaturesBuildReport:
    """Le SQLite, calcula features e exporta parquet em data/processed/."""
    cfg = settings or load_settings()
    ensure_data_dirs(cfg)

    with repository_session(cfg.db_path) as repository:
        context = load_cell_day_context(
            repository,
            cfg,
            include_weather=True,
            step="features",
        )
        rows = build_features_table(
            context.cell_ids,
            context.days,
            context.fires,
            context.weather,
        )
        parquet_path = _export_parquet(cfg.processed_dir, rows)
        logger.info(
            "Features: rows=%s cells=%s days=%s parquet=%s",
            len(rows),
            len(context.cell_ids),
            len(context.days),
            parquet_path,
        )
        return FeaturesBuildReport(
            total_rows=len(rows),
            cell_count=len(context.cell_ids),
            day_count=len(context.days),
            parquet_path=parquet_path,
        )


def _export_parquet(processed_dir: Path, rows: list[CellDayFeatures]) -> Path:
    """Grava features em data/processed/features_cell_day.parquet."""
    data = [
        {
            "cell_id": row.cell_id,
            "day": row.day.isoformat(),
            "fires_7d": row.fires_7d,
            "fires_30d": row.fires_30d,
            "days_without_rain": row.days_without_rain,
            "temp_mean_7d": row.temp_mean_7d,
            "season_month": row.season_month,
        }
        for row in rows
    ]
    return write_parquet(processed_dir, FEATURES_PARQUET, data)


def main() -> None:
    """Entrypoint: python -m src.application.build_features"""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    report = build_features()
    print(
        f"Features: rows={report.total_rows} cells={report.cell_count} "
        f"days={report.day_count} parquet={report.parquet_path}"
    )


if __name__ == "__main__":
    main()
