"""Testes do parser CSV NASA FIRMS (S1.E1)."""

from datetime import datetime

import pytest

from src.config import DEFAULT_BBOX
from src.infrastructure.firms.parser import parse_firms_csv

SAMPLE_CSV = """latitude,longitude,brightness,scan,track,acq_date,acq_time,satellite,instrument,confidence,version,bright_t31,frp,daynight
-10.05,-47.92,320.5,0.5,0.5,2026-06-01,1430,N,VIIRS,85,nrt,285.2,18.4,D
-8.20,-48.30,310.0,0.5,0.5,2026-06-02,304,N,VIIRS,h,nrt,280.0,31.5,N
-30.00,-50.00,290.0,0.5,0.5,2026-06-01,1200,N,VIIRS,n,nrt,270.0,5.0,D
"""


def test_parse_firms_csv_maps_fields() -> None:
    """Parser deve montar datetime e campos numericos."""
    events = parse_firms_csv(SAMPLE_CSV, source="VIIRS_NRT", bbox=DEFAULT_BBOX)
    assert len(events) == 2
    first = events[0]
    assert first.source == "VIIRS_NRT"
    assert first.acq_datetime == datetime(2026, 6, 1, 14, 30)
    assert first.lat == pytest.approx(-10.05)
    assert first.lon == pytest.approx(-47.92)
    assert first.confidence == pytest.approx(85.0)
    assert first.frp == pytest.approx(18.4)


def test_parse_firms_csv_filters_bbox() -> None:
    """Pontos fora do Tocantins devem ser descartados."""
    events = parse_firms_csv(SAMPLE_CSV, source="VIIRS_NRT", bbox=DEFAULT_BBOX)
    lats = {event.lat for event in events}
    assert -30.0 not in lats


def test_parse_confidence_nominal() -> None:
    """Confidence nominal h deve virar valor numerico."""
    events = parse_firms_csv(SAMPLE_CSV, source="VIIRS_NRT", bbox=DEFAULT_BBOX)
    second = events[1]
    assert second.confidence == pytest.approx(80.0)
    assert second.acq_datetime == datetime(2026, 6, 2, 3, 4)


def test_parse_firms_csv_empty() -> None:
    """CSV vazio retorna lista vazia sem erro."""
    assert parse_firms_csv("", source="MODIS_NRT") == []


def test_parse_firms_csv_missing_columns() -> None:
    """Colunas obrigatorias ausentes geram ValueError."""
    bad_csv = "latitude,longitude\n-16.0,-47.0\n"
    with pytest.raises(ValueError, match="colunas obrigatorias"):
        parse_firms_csv(bad_csv, source="MODIS_NRT")
