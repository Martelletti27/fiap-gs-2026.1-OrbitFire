"""Testes do caso de uso build_features (S2.E1)."""

from dataclasses import replace
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import pytest

from src.application.build_features import build_features
from src.application.processed_io import FEATURES_PARQUET
from src.config import BBox, load_settings
from src.domain.cell_id import build_grid_cells
from src.infrastructure.db.repository import open_repository

TEST_BBOX = BBox(lat_min=-16.15, lat_max=-15.75, lon_min=-48.30, lon_max=-47.40)


@pytest.fixture
def features_settings(tmp_path: Path):
    """Settings com grade pequena e paths temporarios."""
    base = load_settings(env_file=Path("/arquivo/inexistente.env"))
    return replace(
        base,
        bbox=TEST_BBOX,
        db_path=tmp_path / "orbitfire.db",
        processed_dir=tmp_path / "processed",
    )


def _seed_grid_and_data(settings) -> int:
    """Popula grade, focos e clima minimos; retorna qtd de celulas."""
    specs = build_grid_cells(settings.bbox, settings.grid_deg)
    repo, session, engine = open_repository(settings.db_path)
    try:
        for spec in specs:
            repo.add_grid_cell(spec.cell_id, spec.lat_center, spec.lon_center, spec.uf)
        repo.add_fire_event(
            "VIIRS_NRT",
            datetime(2026, 6, 2, 14, 0),
            -15.80,
            -47.90,
        )
        repo.add_weather_daily(
            specs[0].cell_id,
            date(2026, 6, 1),
            temp_max=28.0,
            precip_mm=0.0,
        )
        repo.add_weather_daily(
            specs[0].cell_id,
            date(2026, 6, 2),
            temp_max=30.0,
            precip_mm=0.0,
        )
        return len(specs)
    finally:
        session.close()
        engine.dispose()


def test_build_features_exports_parquet(features_settings) -> None:
    """Deve gerar parquet com colunas esperadas."""
    cell_count = _seed_grid_and_data(features_settings)
    report = build_features(features_settings)

    assert report.cell_count == cell_count
    assert report.day_count >= 2
    assert report.total_rows == cell_count * report.day_count
    assert report.parquet_path.is_file()

    df = pd.read_parquet(report.parquet_path)
    assert set(df.columns) == {
        "cell_id",
        "day",
        "fires_7d",
        "fires_30d",
        "days_without_rain",
        "temp_mean_7d",
        "season_month",
    }


def test_build_features_requires_grid(features_settings) -> None:
    """Grade vazia deve falhar com mensagem clara."""
    with pytest.raises(ValueError, match="Grade vazia"):
        build_features(features_settings)


def test_parquet_path_under_processed(features_settings) -> None:
    """Arquivo deve ficar em data/processed/features_cell_day.parquet."""
    _seed_grid_and_data(features_settings)
    report = build_features(features_settings)
    assert report.parquet_path == features_settings.processed_dir / FEATURES_PARQUET
