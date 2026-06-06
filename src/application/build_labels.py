"""Caso de uso: labels binarios de fogo amanha por celula e dia."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from src.application.db_loaders import load_cell_day_context
from src.application.processed_io import LABELS_PARQUET, write_parquet
from src.config import Settings, ensure_data_dirs, load_settings
from src.domain.labels import CellDayLabel, build_labels_table
from src.infrastructure.db.repository import repository_session

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LabelsBuildReport:
    """Resumo da geracao de labels."""

    total_rows: int
    positive_labels: int
    cell_count: int
    day_count: int
    parquet_path: Path


def build_labels(settings: Settings | None = None) -> LabelsBuildReport:
    """Le focos do SQLite, calcula labels D+1 e exporta parquet."""
    cfg = settings or load_settings()
    ensure_data_dirs(cfg)

    with repository_session(cfg.db_path) as repository:
        context = load_cell_day_context(
            repository,
            cfg,
            include_weather=True,
            step="labels",
        )
        print(
            f"Calculando labels: {len(context.cell_ids)} celulas x "
            f"{len(context.days)} dias...",
            flush=True,
        )
        rows = build_labels_table(context.cell_ids, context.days, context.fires)
        print("Exportando parquet...", flush=True)
        parquet_path = _export_parquet(cfg.processed_dir, rows)
        positives = sum(row.fire_tomorrow for row in rows)
        logger.info(
            "Labels: rows=%s positive=%s cells=%s days=%s parquet=%s",
            len(rows),
            positives,
            len(context.cell_ids),
            len(context.days),
            parquet_path,
        )
        return LabelsBuildReport(
            total_rows=len(rows),
            positive_labels=positives,
            cell_count=len(context.cell_ids),
            day_count=len(context.days),
            parquet_path=parquet_path,
        )


def _export_parquet(processed_dir: Path, rows: list[CellDayLabel]) -> Path:
    """Grava labels em data/processed/labels_cell_day.parquet."""
    data = [
        {
            "cell_id": row.cell_id,
            "day": row.day.isoformat(),
            "fire_tomorrow": row.fire_tomorrow,
        }
        for row in rows
    ]
    return write_parquet(processed_dir, LABELS_PARQUET, data)


def main() -> None:
    """Entrypoint: python -m src.application.build_labels"""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    report = build_labels()
    print(
        f"Labels: rows={report.total_rows} positive={report.positive_labels} "
        f"cells={report.cell_count} days={report.day_count} "
        f"parquet={report.parquet_path}"
    )


if __name__ == "__main__":
    main()
