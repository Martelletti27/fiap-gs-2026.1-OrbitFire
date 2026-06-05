"""Parser da resposta JSON diaria do Open-Meteo."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class ParsedWeatherDaily:
    """Registro climatico diario normalizado."""

    day: date
    temp_max: float | None
    temp_min: float | None
    precip_mm: float | None
    wind_speed: float | None


def parse_open_meteo_daily(payload: dict) -> list[ParsedWeatherDaily]:
    """Converte bloco daily do JSON Open-Meteo em registros tipados."""
    daily = payload.get("daily")
    if not daily:
        return []

    times = daily.get("time") or []
    if not times:
        return []

    records: list[ParsedWeatherDaily] = []
    for index, day_text in enumerate(times):
        records.append(
            ParsedWeatherDaily(
                day=date.fromisoformat(day_text),
                temp_max=_value_at(daily.get("temperature_2m_max"), index),
                temp_min=_value_at(daily.get("temperature_2m_min"), index),
                precip_mm=_value_at(daily.get("precipitation_sum"), index),
                wind_speed=_value_at(daily.get("wind_speed_10m_max"), index),
            )
        )

    return records


def _value_at(values: list | None, index: int) -> float | None:
    """Le valor float na posicao; None se ausente ou null."""
    if not values or index >= len(values):
        return None
    raw = values[index]
    if raw is None:
        return None
    return float(raw)
