"""Testes da grade e cell_id (S1.E3)."""

import pytest

from src.config import DEFAULT_BBOX, GRID_DEG
from src.domain.cell_id import (
    assign_uf,
    build_grid_cells,
    format_cell_id,
    iter_grid_centers,
    parse_cell_center,
)


def test_format_cell_id_matches_seed_pattern() -> None:
    """cell_id deve seguir UF_lat_lon com duas casas."""
    assert format_cell_id(-15.8, -47.9, "DF") == "DF_-15.80_-47.90"


def test_parse_cell_center_roundtrip() -> None:
    """parse_cell_center deve extrair coordenadas do cell_id."""
    lat, lon = parse_cell_center("GO_-16.00_-49.10")
    assert lat == pytest.approx(-16.0)
    assert lon == pytest.approx(-49.1)


def test_assign_uf_known_points() -> None:
    """Pontos conhecidos devem mapear para UF esperada."""
    assert assign_uf(-15.8, -47.9) == "DF"
    assert assign_uf(-16.0, -49.1) == "GO"
    assert assign_uf(-12.5, -55.1) == "MT"
    assert assign_uf(-20.4, -54.6) == "MS"


def test_iter_grid_centers_respects_bbox() -> None:
    """Todos os centros devem ficar dentro do Centro-Oeste."""
    centers = list(iter_grid_centers(DEFAULT_BBOX, GRID_DEG))
    assert len(centers) > 1000
    for lat, lon in centers:
        assert DEFAULT_BBOX.contains(lat, lon)


def test_build_grid_cells_unique_ids() -> None:
    """Grade completa nao deve repetir cell_id."""
    cells = build_grid_cells(DEFAULT_BBOX, GRID_DEG)
    ids = [cell.cell_id for cell in cells]
    assert len(ids) == len(set(ids))
    assert all(cell.uf in {"GO", "MT", "MS", "DF", None} for cell in cells)
