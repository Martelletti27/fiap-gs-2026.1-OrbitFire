"""Grade geografica e identificador de celula (UF_lat_lon)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

from src.config import BBox, DEFAULT_BBOX, UFS

# Bboxes aproximados por UF para atribuicao na grade (ordem: DF primeiro)
UF_BOXES: tuple[tuple[str, BBox], ...] = (
    ("DF", BBox(lat_min=-16.10, lat_max=-15.45, lon_min=-48.35, lon_max=-47.30)),
    ("GO", BBox(lat_min=-19.90, lat_max=-12.00, lon_min=-53.40, lon_max=-45.80)),
    ("MS", BBox(lat_min=-24.10, lat_max=-17.00, lon_min=-58.50, lon_max=-50.00)),
    ("MT", BBox(lat_min=-18.10, lat_max=-12.00, lon_min=-61.60, lon_max=-50.00)),
)


@dataclass(frozen=True)
class GridCellSpec:
    """Celula da grade antes da persistencia."""

    cell_id: str
    lat_center: float
    lon_center: float
    uf: str | None


def iter_grid_centers(bbox: BBox, grid_deg: float) -> Iterator[tuple[float, float]]:
    """Gera centros de celulas dentro do bbox com passo grid_deg."""
    half = grid_deg / 2.0
    lat = bbox.lat_min + half
    while lat <= bbox.lat_max + 1e-9:
        lon = bbox.lon_min + half
        while lon <= bbox.lon_max + 1e-9:
            if bbox.contains(lat, lon):
                yield round(lat, 4), round(lon, 4)
            lon += grid_deg
        lat += grid_deg


def assign_uf(lat: float, lon: float) -> str | None:
    """Atribui UF por bbox aproximado; None se fora das UFs conhecidas."""
    for uf, uf_box in UF_BOXES:
        if uf in UFS and uf_box.contains(lat, lon):
            return uf
    return None


def format_cell_id(lat_center: float, lon_center: float, uf: str | None = None) -> str:
    """Monta cell_id no padrao UF_lat_lon com duas casas decimais."""
    lat_text = f"{lat_center:.2f}"
    lon_text = f"{lon_center:.2f}"
    if uf:
        return f"{uf}_{lat_text}_{lon_text}"
    return f"{lat_text}_{lon_text}"


def parse_cell_center(cell_id: str) -> tuple[float, float]:
    """Extrai lat/lon do formato UF_lat_lon."""
    parts = cell_id.split("_")
    if len(parts) < 2:
        raise ValueError(f"cell_id invalido: {cell_id}")
    return float(parts[-2]), float(parts[-1])


def build_grid_cells(
    bbox: BBox = DEFAULT_BBOX,
    grid_deg: float = 0.10,
) -> list[GridCellSpec]:
    """Constroi todas as celulas do Centro-Oeste para a grade configurada."""
    cells: list[GridCellSpec] = []
    for lat, lon in iter_grid_centers(bbox, grid_deg):
        uf = assign_uf(lat, lon)
        cells.append(
            GridCellSpec(
                cell_id=format_cell_id(lat, lon, uf),
                lat_center=lat,
                lon_center=lon,
                uf=uf,
            )
        )
    return cells
