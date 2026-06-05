"""Testes do calculo puro de features (S2.E1)."""

from datetime import date

import pytest

from src.config import BBox, DEFAULT_BBOX, GRID_DEG
from src.domain.cell_id import snap_point_to_cell_id
from src.domain.features import FirePoint, WeatherPoint, build_cell_day_features

TEST_BBOX = BBox(lat_min=-16.15, lat_max=-15.75, lon_min=-48.30, lon_max=-47.40)


def test_snap_point_to_cell_id_aligns_with_grid() -> None:
    """Coordenada dentro do bbox deve cair em cell_id valido."""
    cell_id = snap_point_to_cell_id(-15.80, -47.90, TEST_BBOX, GRID_DEG)
    assert cell_id is not None
    assert cell_id.startswith("DF_")


def test_build_cell_day_features_fires_windows() -> None:
    """Janelas 7d e 30d devem contar focos corretamente."""
    ref = date(2026, 6, 10)
    fires = [
        FirePoint("DF_-15.80_-47.90", date(2026, 6, 10)),
        FirePoint("DF_-15.80_-47.90", date(2026, 6, 5)),
        FirePoint("DF_-15.80_-47.90", date(2026, 5, 1)),
    ]
    row = build_cell_day_features("DF_-15.80_-47.90", ref, fires, [])
    assert row.fires_7d == 2
    assert row.fires_30d == 2


def test_build_cell_day_features_days_without_rain() -> None:
    """Deve contar dias seguidos sem precipitacao significativa."""
    ref = date(2026, 6, 5)
    weather = [
        WeatherPoint("GO_-16.00_-49.10", date(2026, 6, 5), 30.0, 0.0),
        WeatherPoint("GO_-16.00_-49.10", date(2026, 6, 4), 29.0, 0.0),
        WeatherPoint("GO_-16.00_-49.10", date(2026, 6, 3), 28.0, 2.0),
    ]
    row = build_cell_day_features("GO_-16.00_-49.10", ref, [], weather)
    assert row.days_without_rain == 2


def test_build_cell_day_features_temp_mean_7d() -> None:
    """Media termica usa temp_max dos dias com dado na janela."""
    ref = date(2026, 6, 3)
    weather = [
        WeatherPoint("MT_-12.50_-55.10", date(2026, 6, 1), 32.0, 0.0),
        WeatherPoint("MT_-12.50_-55.10", date(2026, 6, 2), 34.0, 0.0),
        WeatherPoint("MT_-12.50_-55.10", date(2026, 6, 3), 30.0, 0.0),
    ]
    row = build_cell_day_features("MT_-12.50_-55.10", ref, [], weather)
    assert row.temp_mean_7d == pytest.approx(32.0)


def test_build_cell_day_features_season_month() -> None:
    """Sazonalidade reflete o mes da data de referencia."""
    row = build_cell_day_features("MS_-20.40_-54.60", date(2026, 3, 15), [], [])
    assert row.season_month == 3


def test_snap_point_outside_bbox_returns_none() -> None:
    """Ponto fora do Centro-Oeste nao gera cell_id."""
    assert snap_point_to_cell_id(-30.0, -50.0, DEFAULT_BBOX, GRID_DEG) is None
