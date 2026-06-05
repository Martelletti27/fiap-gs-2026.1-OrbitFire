"""Caso de uso: gerar grade do Centro-Oeste e persistir."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from src.config import Settings, ensure_data_dirs, load_settings
from src.domain.cell_id import GridCellSpec, build_grid_cells
from src.infrastructure.db.repository import OrbitFireRepository, open_repository, tally_insert

logger = logging.getLogger(__name__)

GRID_PARQUET_NAME = "grid_cells.parquet"


@dataclass(frozen=True)
class GridBuildReport:
    """Resumo da geracao e persistencia da grade."""

    total_cells: int
    inserted: int
    skipped: int
    parquet_path: Path


def build_and_persist_grid(settings: Settings | None = None) -> GridBuildReport:
    """Gera celulas, grava em SQLite e exporta parquet em data/processed/."""
    cfg = settings or load_settings()
    ensure_data_dirs(cfg)

    specs = build_grid_cells(cfg.bbox, cfg.grid_deg)
    repository, session, engine = open_repository(cfg.db_path)
    try:
        inserted, skipped = _persist_cells(repository, specs)
        parquet_path = _export_parquet(cfg.processed_dir, specs)
        logger.info(
            "Grade: total=%s inserted=%s skipped=%s parquet=%s",
            len(specs),
            inserted,
            skipped,
            parquet_path,
        )
        return GridBuildReport(
            total_cells=len(specs),
            inserted=inserted,
            skipped=skipped,
            parquet_path=parquet_path,
        )
    finally:
        session.close()
        engine.dispose()


def _persist_cells(
    repository: OrbitFireRepository,
    specs: list[GridCellSpec],
) -> tuple[int, int]:
    """Insere celulas com deduplicacao por cell_id."""
    inserted, skipped = 0, 0
    for spec in specs:
        result = repository.add_grid_cell(
            cell_id=spec.cell_id,
            lat_center=spec.lat_center,
            lon_center=spec.lon_center,
            uf=spec.uf,
        )
        inserted, skipped = tally_insert(result, inserted, skipped)
    return inserted, skipped


def _export_parquet(processed_dir: Path, specs: list[GridCellSpec]) -> Path:
    """Exporta snapshot da grade para data/processed/grid_cells.parquet."""
    processed_dir.mkdir(parents=True, exist_ok=True)
    path = processed_dir / GRID_PARQUET_NAME
    rows = [
        {
            "cell_id": spec.cell_id,
            "lat_center": spec.lat_center,
            "lon_center": spec.lon_center,
            "uf": spec.uf,
        }
        for spec in specs
    ]
    pd.DataFrame(rows).to_parquet(path, index=False)
    return path


def main() -> None:
    """Entrypoint: python -m src.application.build_grid"""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    report = build_and_persist_grid()
    print(
        f"Grade: total={report.total_cells} inserted={report.inserted} "
        f"skipped={report.skipped} parquet={report.parquet_path}"
    )


if __name__ == "__main__":
    main()
