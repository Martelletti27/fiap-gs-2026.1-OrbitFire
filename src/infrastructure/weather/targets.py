"""Pontos de coleta de clima por cell_id (grade ou seed)."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from src.config import Settings
from src.domain.cell_id import parse_cell_center
from src.infrastructure.db.repository import OrbitFireRepository
from src.infrastructure.seed.loader import WEATHER_SEED_FILE


@dataclass(frozen=True)
class WeatherTarget:
    """Celula ou ponto representativo para buscar clima diario."""

    cell_id: str
    lat: float
    lon: float


def resolve_weather_targets(
    settings: Settings,
    repository: OrbitFireRepository,
) -> list[WeatherTarget]:
    """Usa grade persistida; se vazia, cai para cell_ids unicos do seed."""
    grid_cells = repository.list_grid_cells()
    if grid_cells:
        return [
            WeatherTarget(
                cell_id=cell.cell_id,
                lat=cell.lat_center,
                lon=cell.lon_center,
            )
            for cell in grid_cells
        ]

    return _targets_from_seed(settings.seed_dir / WEATHER_SEED_FILE)


def _targets_from_seed(path: Path) -> list[WeatherTarget]:
    """Monta alvos unicos a partir do CSV seed de clima."""
    if not path.is_file():
        raise FileNotFoundError(
            "Grade vazia e seed de clima ausente. "
            "Execute S1.E3 (grade) ou forneca data/seed/weather_daily_seed.csv"
        )

    seen: set[str] = set()
    targets: list[WeatherTarget] = []

    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            cell_id = row["cell_id"]
            if cell_id in seen:
                continue
            seen.add(cell_id)
            lat, lon = parse_cell_center(cell_id)
            targets.append(WeatherTarget(cell_id=cell_id, lat=lat, lon=lon))

    return targets
