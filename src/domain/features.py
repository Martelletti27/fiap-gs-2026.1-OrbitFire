"""Calculo puro de features preditivas por celula e dia."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

PRECIP_RAIN_MM = 0.1
FIRE_WINDOW_7D = 7
FIRE_WINDOW_30D = 30
TEMP_WINDOW_7D = 7


@dataclass(frozen=True)
class FirePoint:
    """Foco FIRMS ja mapeado para celula e dia."""

    cell_id: str
    day: date


@dataclass(frozen=True)
class WeatherPoint:
    """Clima diario por celula."""

    cell_id: str
    day: date
    temp_max: float | None
    precip_mm: float | None


@dataclass(frozen=True)
class CellDayFeatures:
    """Features preditivas para uma celula em um dia de referencia."""

    cell_id: str
    day: date
    fires_7d: int
    fires_30d: int
    days_without_rain: int
    temp_mean_7d: float | None
    season_month: int


def build_cell_day_features(
    cell_id: str,
    day: date,
    fires: list[FirePoint],
    weather: list[WeatherPoint],
) -> CellDayFeatures:
    """Monta vetor de features para celula e dia de referencia."""
    cell_fires = [point for point in fires if point.cell_id == cell_id]
    cell_weather = {point.day: point for point in weather if point.cell_id == cell_id}

    return CellDayFeatures(
        cell_id=cell_id,
        day=day,
        fires_7d=_count_fires_in_window(cell_fires, day, FIRE_WINDOW_7D),
        fires_30d=_count_fires_in_window(cell_fires, day, FIRE_WINDOW_30D),
        days_without_rain=_days_without_rain(cell_weather, day),
        temp_mean_7d=_temp_mean_window(cell_weather, day, TEMP_WINDOW_7D),
        season_month=day.month,
    )


def build_features_table(
    cell_ids: list[str],
    days: list[date],
    fires: list[FirePoint],
    weather: list[WeatherPoint],
) -> list[CellDayFeatures]:
    """Gera features para o produto celulas x dias de referencia."""
    ordered_days = sorted(set(days))
    rows: list[CellDayFeatures] = []
    for cell_id in cell_ids:
        for day in ordered_days:
            rows.append(build_cell_day_features(cell_id, day, fires, weather))
    return rows


def _count_fires_in_window(
    fires: list[FirePoint],
    reference: date,
    window_days: int,
) -> int:
    """Conta focos na janela [reference - window + 1, reference]."""
    start = reference - timedelta(days=window_days - 1)
    return sum(1 for point in fires if start <= point.day <= reference)


def _days_without_rain(weather_by_day: dict[date, WeatherPoint], reference: date) -> int:
    """Dias consecutivos sem chuva significativa ate a data de referencia."""
    streak = 0
    cursor = reference
    while cursor in weather_by_day:
        precip = weather_by_day[cursor].precip_mm
        if precip is not None and precip >= PRECIP_RAIN_MM:
            break
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def _temp_mean_window(
    weather_by_day: dict[date, WeatherPoint],
    reference: date,
    window_days: int,
) -> float | None:
    """Media de temp_max nos ultimos N dias com dado disponivel."""
    start = reference - timedelta(days=window_days - 1)
    values: list[float] = []
    for offset in range(window_days):
        day = start + timedelta(days=offset)
        point = weather_by_day.get(day)
        if point is not None and point.temp_max is not None:
            values.append(point.temp_max)
    if not values:
        return None
    return sum(values) / len(values)
