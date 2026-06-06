"""Testes da grade e cell_id (S1.E3)."""

import pytest

from src.config import DEFAULT_BBOX, GRID_DEG
from src.domain.cell_id import (
    assign_uf,
    build_grid_cells,
    format_cell_id,
    iter_grid_centers,
    neighbor_cell_ids,
    parse_cell_center,
)


def test_format_cell_id_matches_seed_pattern() -> None:
    """cell_id deve seguir UF_lat_lon com duas casas."""
    assert format_cell_id(-10.05, -47.90, "TO") == "TO_-10.05_-47.90"


def test_parse_cell_center_roundtrip() -> None:
    """parse_cell_center deve extrair coordenadas do cell_id."""
    lat, lon = parse_cell_center("TO_-10.05_-47.90")
    assert lat == pytest.approx(-10.05)
    assert lon == pytest.approx(-47.9)


def test_assign_uf_known_points() -> None:
    """Pontos no Tocantins devem mapear para TO; fora retorna None."""
    assert assign_uf(-10.05, -47.90) == "TO"
    assert assign_uf(-8.20, -48.30) == "TO"
    assert assign_uf(-15.8, -47.9) is None
    assert assign_uf(-16.0, -49.1) is None


def test_iter_grid_centers_respects_bbox() -> None:
    """Todos os centros devem ficar dentro do Tocantins."""
    centers = list(iter_grid_centers(DEFAULT_BBOX, GRID_DEG))
    assert len(centers) > 1000
    for lat, lon in centers:
        assert DEFAULT_BBOX.contains(lat, lon)


def test_neighbor_cell_ids_returns_eight_adjacent_cells() -> None:
    """Vizinhanca deve seguir passo da grade e respeitar celulas conhecidas."""
    known = {
        "TO_-10.05_-45.75",
        "TO_-9.95_-45.75",
        "TO_-10.05_-45.65",
    }
    neighbors = neighbor_cell_ids("TO_-10.05_-45.75", GRID_DEG, known)
    assert neighbors == ("TO_-9.95_-45.75", "TO_-10.05_-45.65")


def test_build_grid_cells_unique_ids() -> None:
    """Grade completa nao deve repetir cell_id."""
    cells = build_grid_cells(DEFAULT_BBOX, GRID_DEG)
    ids = [cell.cell_id for cell in cells]
    assert len(ids) == len(set(ids))
    assert all(cell.uf == "TO" for cell in cells)
