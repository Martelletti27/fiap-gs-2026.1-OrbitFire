"""Testes do caso de uso build_labels (S2.E2)."""

from dataclasses import replace
from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

from src.application.build_labels import build_labels
from src.application.processed_io import LABELS_PARQUET
from src.config import BBox, load_settings
from src.domain.cell_id import build_grid_cells
from src.infrastructure.db.repository import open_repository

TEST_BBOX = BBox(lat_min=-16.15, lat_max=-15.75, lon_min=-48.30, lon_max=-47.40)


@pytest.fixture
def labels_settings(tmp_path: Path):
    """Settings com grade pequena e paths temporarios."""
    base = load_settings(env_file=Path("/arquivo/inexistente.env"))
    return replace(
        base,
        bbox=TEST_BBOX,
        db_path=tmp_path / "orbitfire.db",
        processed_dir=tmp_path / "processed",
    )


def _seed_grid_and_fires(settings) -> int:
    """Popula grade e focos; retorna quantidade de celulas."""
    specs = build_grid_cells(settings.bbox, settings.grid_deg)
    repo, session, engine = open_repository(settings.db_path)
    try:
        for spec in specs:
            repo.add_grid_cell(spec.cell_id, spec.lat_center, spec.lon_center, spec.uf)
        cell_id = specs[0].cell_id
        repo.add_fire_event(
            "VIIRS_NRT",
            datetime(2026, 6, 1, 12, 0),
            -15.80,
            -47.90,
            cell_id=cell_id,
        )
        repo.add_fire_event(
            "VIIRS_NRT",
            datetime(2026, 6, 2, 14, 0),
            -15.80,
            -47.90,
            cell_id=cell_id,
        )
        return len(specs)
    finally:
        session.close()
        engine.dispose()


def test_build_labels_exports_parquet(labels_settings) -> None:
    """Deve gerar parquet com label binario."""
    cell_count = _seed_grid_and_fires(labels_settings)
    report = build_labels(labels_settings)

    assert report.cell_count == cell_count
    assert report.day_count == 2
    assert report.positive_labels >= 1
    assert report.parquet_path.is_file()

    df = pd.read_parquet(report.parquet_path)
    assert set(df.columns) == {"cell_id", "day", "fire_tomorrow"}
    assert df["fire_tomorrow"].isin([0, 1]).all()


def test_build_labels_requires_grid(labels_settings) -> None:
    """Grade vazia deve falhar com mensagem clara."""
    with pytest.raises(ValueError, match="Grade vazia"):
        build_labels(labels_settings)


def test_parquet_path_under_processed(labels_settings) -> None:
    """Arquivo deve ficar em data/processed/labels_cell_day.parquet."""
    _seed_grid_and_fires(labels_settings)
    report = build_labels(labels_settings)
    assert report.parquet_path == labels_settings.processed_dir / LABELS_PARQUET
