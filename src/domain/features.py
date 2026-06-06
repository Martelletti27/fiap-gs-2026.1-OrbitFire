"""Calculo puro de features preditivas por celula e dia."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from src.domain.cell_id import neighbor_cell_ids

PRECIP_RAIN_MM = 0.1
FIRE_WINDOW_1D = 1
FIRE_WINDOW_7D = 7
FIRE_WINDOW_30D = 30
WEATHER_WINDOW_7D = 7
PROGRESS_EVERY_CELLS = 100

FEATURE_COLUMN_NAMES: tuple[str, ...] = (
    "fires_1d",
    "fires_7d",
    "fires_30d",
    "days_without_rain",
    "temp_mean_7d",
    "precip_sum_7d",
    "wind_mean_7d",
    "neighbor_fires_7d",
    "season_month",
)


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
    wind_speed: float | None = None


@dataclass(frozen=True)
class CellDayFeatures:
    """Features preditivas para uma celula em um dia de referencia."""

    cell_id: str
    day: date
    fires_1d: int
    fires_7d: int
    fires_30d: int
    days_without_rain: int
    temp_mean_7d: float | None
    precip_sum_7d: float | None
    wind_mean_7d: float | None
    neighbor_fires_7d: int
    season_month: int


def cell_day_features_to_record(row: CellDayFeatures) -> dict[str, object]:
    """Serializa features para parquet ou export tabular."""
    return {
        "cell_id": row.cell_id,
        "day": row.day.isoformat(),
        "fires_1d": row.fires_1d,
        "fires_7d": row.fires_7d,
        "fires_30d": row.fires_30d,
        "days_without_rain": row.days_without_rain,
        "temp_mean_7d": row.temp_mean_7d,
        "precip_sum_7d": row.precip_sum_7d,
        "wind_mean_7d": row.wind_mean_7d,
        "neighbor_fires_7d": row.neighbor_fires_7d,
        "season_month": row.season_month,
    }


def build_cell_day_features(
    cell_id: str,
    day: date,
    fires: list[FirePoint],
    weather: list[WeatherPoint],
    grid_deg: float = 0.10,
    known_cells: frozenset[str] | set[str] | None = None,
) -> CellDayFeatures:
    """Monta vetor de features para celula e dia de referencia."""
    fire_counts_by_cell = _group_fire_counts(fires)
    fire_counts = fire_counts_by_cell.get(cell_id, {})
    weather_by_day = {
        point.day: point for point in weather if point.cell_id == cell_id
    }
    if known_cells is None:
        known_cells = frozenset(fire_counts_by_cell.keys())
    neighbor_ids = neighbor_cell_ids(cell_id, grid_deg, known_cells)
    return _features_from_prepared(
        cell_id,
        day,
        fire_counts,
        weather_by_day,
        neighbor_ids,
        fire_counts_by_cell,
    )


def build_features_table(
    cell_ids: list[str],
    days: list[date],
    fires: list[FirePoint],
    weather: list[WeatherPoint],
    grid_deg: float = 0.10,
) -> list[CellDayFeatures]:
    """Gera features para o produto celulas x dias de referencia.

    Agrupa focos e clima por celula uma unica vez para evitar refiltrar
    todas as deteccoes a cada linha (essencial com volume historico SP).
    """
    ordered_days = sorted(set(days))
    total_cells = len(cell_ids)
    fire_counts_by_cell = _group_fire_counts(fires)
    weather_by_cell = _group_weather(weather)
    known_cells = frozenset(cell_ids)
    neighbors_by_cell = {
        cell_id: neighbor_cell_ids(cell_id, grid_deg, known_cells)
        for cell_id in cell_ids
    }

    rows: list[CellDayFeatures] = []
    for index, cell_id in enumerate(cell_ids, start=1):
        fire_counts = fire_counts_by_cell.get(cell_id, {})
        weather_by_day = weather_by_cell.get(cell_id, {})
        neighbor_ids = neighbors_by_cell[cell_id]
        for day in ordered_days:
            rows.append(
                _features_from_prepared(
                    cell_id,
                    day,
                    fire_counts,
                    weather_by_day,
                    neighbor_ids,
                    fire_counts_by_cell,
                )
            )
        if index % PROGRESS_EVERY_CELLS == 0 or index == total_cells:
            _print_features_progress(index, total_cells)
    return rows


def _features_from_prepared(
    cell_id: str,
    day: date,
    fire_counts: dict[date, int],
    weather_by_day: dict[date, WeatherPoint],
    neighbor_ids: tuple[str, ...] = (),
    fire_counts_by_cell: dict[str, dict[date, int]] | None = None,
) -> CellDayFeatures:
    """Calcula features a partir de estruturas ja indexadas por dia."""
    return CellDayFeatures(
        cell_id=cell_id,
        day=day,
        fires_1d=_count_fires_in_window(fire_counts, day, FIRE_WINDOW_1D),
        fires_7d=_count_fires_in_window(fire_counts, day, FIRE_WINDOW_7D),
        fires_30d=_count_fires_in_window(fire_counts, day, FIRE_WINDOW_30D),
        days_without_rain=_days_without_rain(weather_by_day, day),
        temp_mean_7d=_temp_mean_window(weather_by_day, day, WEATHER_WINDOW_7D),
        precip_sum_7d=_precip_sum_window(weather_by_day, day, WEATHER_WINDOW_7D),
        wind_mean_7d=_wind_mean_window(weather_by_day, day, WEATHER_WINDOW_7D),
        neighbor_fires_7d=_count_neighbor_fires_in_window(
            fire_counts_by_cell or {},
            neighbor_ids,
            day,
            FIRE_WINDOW_7D,
        ),
        season_month=day.month,
    )


def _group_fire_counts(fires: list[FirePoint]) -> dict[str, dict[date, int]]:
    """Indexa contagem de focos por celula e dia."""
    result: dict[str, dict[date, int]] = {}
    for point in fires:
        by_day = result.setdefault(point.cell_id, {})
        by_day[point.day] = by_day.get(point.day, 0) + 1
    return result


def _group_weather(weather: list[WeatherPoint]) -> dict[str, dict[date, WeatherPoint]]:
    """Indexa clima por celula e dia."""
    result: dict[str, dict[date, WeatherPoint]] = {}
    for point in weather:
        result.setdefault(point.cell_id, {})[point.day] = point
    return result


def _count_fires_in_window(
    fire_counts: dict[date, int],
    reference: date,
    window_days: int,
) -> int:
    """Conta focos na janela [reference - window + 1, reference]."""
    start = reference - timedelta(days=window_days - 1)
    return sum(
        count
        for day, count in fire_counts.items()
        if start <= day <= reference
    )


def _count_neighbor_fires_in_window(
    fire_counts_by_cell: dict[str, dict[date, int]],
    neighbor_ids: tuple[str, ...],
    reference: date,
    window_days: int,
) -> int:
    """Soma focos das celulas vizinhas na janela temporal."""
    total = 0
    for neighbor_id in neighbor_ids:
        counts = fire_counts_by_cell.get(neighbor_id, {})
        total += _count_fires_in_window(counts, reference, window_days)
    return total


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
    return _weather_mean_window(
        weather_by_day,
        reference,
        window_days,
        lambda point: point.temp_max,
    )


def _precip_sum_window(
    weather_by_day: dict[date, WeatherPoint],
    reference: date,
    window_days: int,
) -> float | None:
    """Soma de precip_mm nos ultimos N dias com dado disponivel."""
    start = reference - timedelta(days=window_days - 1)
    total = 0.0
    has_value = False
    for offset in range(window_days):
        day = start + timedelta(days=offset)
        point = weather_by_day.get(day)
        if point is not None and point.precip_mm is not None:
            total += point.precip_mm
            has_value = True
    if not has_value:
        return None
    return total


def _wind_mean_window(
    weather_by_day: dict[date, WeatherPoint],
    reference: date,
    window_days: int,
) -> float | None:
    """Media de wind_speed nos ultimos N dias com dado disponivel."""
    return _weather_mean_window(
        weather_by_day,
        reference,
        window_days,
        lambda point: point.wind_speed,
    )


def _weather_mean_window(
    weather_by_day: dict[date, WeatherPoint],
    reference: date,
    window_days: int,
    extractor,
) -> float | None:
    """Media de um campo numerico do clima na janela [ref - N + 1, ref]."""
    start = reference - timedelta(days=window_days - 1)
    values: list[float] = []
    for offset in range(window_days):
        day = start + timedelta(days=offset)
        point = weather_by_day.get(day)
        if point is None:
            continue
        value = extractor(point)
        if value is not None:
            values.append(value)
    if not values:
        return None
    return sum(values) / len(values)


def _print_features_progress(done: int, total: int) -> None:
    """Exibe progresso da geracao de features por celula."""
    percent = 100.0 * done / total if total else 100.0
    print(f"Progresso features: {done}/{total} ({percent:.1f}%)", flush=True)
