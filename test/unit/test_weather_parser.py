"""Testes do parser Open-Meteo (S1.E2)."""

from datetime import date

from src.infrastructure.weather.parser import parse_open_meteo_daily

SAMPLE_PAYLOAD = {
    "daily": {
        "time": ["2026-06-01", "2026-06-02"],
        "temperature_2m_max": [29.5, 30.1],
        "temperature_2m_min": [18.2, 17.9],
        "precipitation_sum": [0.0, 1.2],
        "wind_speed_10m_max": [2.8, 3.1],
    }
}


def test_parse_open_meteo_daily_maps_fields() -> None:
    """Parser deve converter arrays daily em registros tipados."""
    records = parse_open_meteo_daily(SAMPLE_PAYLOAD)
    assert len(records) == 2
    first = records[0]
    assert first.day == date(2026, 6, 1)
    assert first.temp_max == 29.5
    assert first.temp_min == 18.2
    assert first.precip_mm == 0.0
    assert first.wind_speed == 2.8


def test_parse_open_meteo_daily_empty() -> None:
    """Payload sem daily retorna lista vazia."""
    assert parse_open_meteo_daily({}) == []
