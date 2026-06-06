"""Carrega pontos do SQLite para casos de uso em application/."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from src.config import BBox, Settings
from src.domain.cell_id import snap_point_to_cell_id
from src.domain.features import FirePoint, WeatherPoint
from src.infrastructure.db.repository import OrbitFireRepository
from src.infrastructure.db.schema import GridCell


@dataclass(frozen=True)
class CellDayBuildContext:
    """Dados compartilhados para geracao de features e labels."""

    cell_ids: list[str]
    fires: list[FirePoint]
    days: list[date]
    weather: list[WeatherPoint]


def require_non_empty_grid(repository: OrbitFireRepository, step: str) -> list[GridCell]:
    """Exige grade persistida antes de features ou labels."""
    grid_cells = repository.list_grid_cells()
    if not grid_cells:
        raise ValueError(
            f"Grade vazia: execute python -m src.application.build_grid antes de {step}"
        )
    return grid_cells


def load_cell_day_context(
    repository: OrbitFireRepository,
    cfg: Settings,
    *,
    include_weather: bool,
    step: str,
) -> CellDayBuildContext:
    """Carrega grade, focos e dias de referencia para pipeline S2."""
    print("Carregando grade...", flush=True)
    grid_cells = require_non_empty_grid(repository, step)
    print(f"Grade: {len(grid_cells)} celulas", flush=True)
    print("Carregando focos FIRMS...", flush=True)
    fires = load_fire_points(repository, cfg.bbox, cfg.grid_deg)
    print(f"Focos: {len(fires)} pontos", flush=True)
    if include_weather:
        print("Carregando clima...", flush=True)
    weather = load_weather_points(repository) if include_weather else []
    if include_weather:
        print(f"Clima: {len(weather)} registros", flush=True)
    days = collect_reference_days(fires, weather)
    if not days:
        if include_weather:
            raise ValueError("Sem dados de focos ou clima para gerar features")
        raise ValueError("Sem dados de focos FIRMS para gerar labels")
    return CellDayBuildContext(
        cell_ids=[cell.cell_id for cell in grid_cells],
        fires=fires,
        days=days,
        weather=weather,
    )


def load_fire_points(
    repository: OrbitFireRepository,
    bbox: BBox,
    grid_deg: float,
) -> list[FirePoint]:
    """Converte focos FIRMS em pontos por celula e dia."""
    points: list[FirePoint] = []
    for event in repository.list_fire_events():
        cell_id = event.cell_id or snap_point_to_cell_id(
            event.lat, event.lon, bbox, grid_deg
        )
        if cell_id is None:
            continue
        points.append(FirePoint(cell_id=cell_id, day=event.acq_datetime.date()))
    return points


def load_weather_points(repository: OrbitFireRepository) -> list[WeatherPoint]:
    """Carrega clima diario do repositorio."""
    return [
        WeatherPoint(
            cell_id=row.cell_id,
            day=row.day,
            temp_max=row.temp_max,
            precip_mm=row.precip_mm,
            wind_speed=row.wind_speed,
        )
        for row in repository.list_weather_daily()
    ]


def collect_reference_days(
    fires: list[FirePoint],
    weather: list[WeatherPoint],
) -> list[date]:
    """Uniao ordenada de dias com foco ou clima."""
    days = {point.day for point in fires}
    days.update(point.day for point in weather)
    return sorted(days)
