"""Testes do caso de uso build_grid (S1.E3)."""

from dataclasses import replace
from pathlib import Path

import pandas as pd
import pytest

from src.application.build_grid import build_and_persist_grid
from src.application.processed_io import GRID_CELLS_PARQUET
from src.config import BBox, load_settings
from src.domain.cell_id import build_grid_cells
from src.infrastructure.db.repository import open_repository

# Bbox pequena (DF) para testes rapidos sem percorrer a grade inteira
TEST_BBOX = BBox(lat_min=-16.15, lat_max=-15.75, lon_min=-48.30, lon_max=-47.40)


@pytest.fixture
def grid_settings(tmp_path: Path):
    """Settings com BD, processed e bbox reduzida para testes."""
    base = load_settings(env_file=Path("/arquivo/inexistente.env"))
    return replace(
        base,
        bbox=TEST_BBOX,
        db_path=tmp_path / "orbitfire.db",
        processed_dir=tmp_path / "processed",
    )


def test_build_and_persist_grid_inserts_and_exports_parquet(grid_settings) -> None:
    """Deve popular grid_cells e gerar parquet."""
    expected = len(build_grid_cells(grid_settings.bbox, grid_settings.grid_deg))
    report = build_and_persist_grid(grid_settings)

    assert report.total_cells == expected
    assert report.inserted == expected
    assert report.skipped == 0
    assert report.parquet_path.is_file()

    df = pd.read_parquet(report.parquet_path)
    assert len(df) == expected
    assert set(df.columns) == {"cell_id", "lat_center", "lon_center", "uf"}

    repo, session, engine = open_repository(grid_settings.db_path)
    try:
        assert repo.count_grid_cells() == expected
    finally:
        session.close()
        engine.dispose()


def test_build_and_persist_grid_is_idempotent(grid_settings) -> None:
    """Segunda execucao nao deve duplicar celulas."""
    first = build_and_persist_grid(grid_settings)
    second = build_and_persist_grid(grid_settings)

    assert first.inserted == first.total_cells
    assert second.inserted == 0
    assert second.skipped == second.total_cells

    repo, session, engine = open_repository(grid_settings.db_path)
    try:
        assert repo.count_grid_cells() == first.total_cells
    finally:
        session.close()
        engine.dispose()


def test_parquet_written_to_processed_dir(grid_settings) -> None:
    """Arquivo deve ficar em data/processed/grid_cells.parquet."""
    report = build_and_persist_grid(grid_settings)
    assert report.parquet_path == grid_settings.processed_dir / GRID_CELLS_PARQUET
