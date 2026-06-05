"""Parser do CSV retornado pela API NASA FIRMS."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import datetime

from src.config import BBox

REQUIRED_COLUMNS = ("latitude", "longitude", "acq_date", "acq_time")
CONFIDENCE_MAP = {"n": 30.0, "l": 50.0, "h": 80.0}


@dataclass(frozen=True)
class ParsedFireEvent:
    """Deteccao normalizada antes da persistencia."""

    source: str
    acq_datetime: datetime
    lat: float
    lon: float
    confidence: float | None
    frp: float | None


def parse_firms_csv(
    csv_text: str,
    *,
    source: str,
    bbox: BBox | None = None,
) -> list[ParsedFireEvent]:
    """Converte CSV NASA em eventos tipados; filtra bbox quando informado."""
    if not csv_text.strip():
        return []

    reader = csv.DictReader(io.StringIO(csv_text))
    if reader.fieldnames is None:
        return []

    _validate_columns(reader.fieldnames)
    events: list[ParsedFireEvent] = []

    for row in reader:
        lat = float(row["latitude"])
        lon = float(row["longitude"])
        if bbox is not None and not bbox.contains(lat, lon):
            continue

        events.append(
            ParsedFireEvent(
                source=source,
                acq_datetime=_parse_acq_datetime(row["acq_date"], row["acq_time"]),
                lat=lat,
                lon=lon,
                confidence=_parse_confidence(row.get("confidence")),
                frp=_parse_optional_float(row.get("frp")),
            )
        )

    return events


def _validate_columns(fieldnames: list[str]) -> None:
    """Garante colunas minimas do CSV NASA."""
    missing = [name for name in REQUIRED_COLUMNS if name not in fieldnames]
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"CSV FIRMS sem colunas obrigatorias: {joined}")


def _parse_acq_datetime(acq_date: str, acq_time: str) -> datetime:
    """Combina acq_date (YYYY-MM-DD) e acq_time (HHMM) em datetime."""
    time_digits = acq_time.strip().zfill(4)
    hour = int(time_digits[:2])
    minute = int(time_digits[2:4])
    year, month, day = (int(part) for part in acq_date.split("-"))
    return datetime(year, month, day, hour, minute)


def _parse_confidence(value: str | None) -> float | None:
    """Aceita numerico ou nominal (n/l/h) do FIRMS."""
    if value is None or value.strip() == "":
        return None
    raw = value.strip().lower()
    if raw in CONFIDENCE_MAP:
        return CONFIDENCE_MAP[raw]
    return float(raw)


def _parse_optional_float(value: str | None) -> float | None:
    """Converte campo vazio em None."""
    if value is None or value.strip() == "":
        return None
    return float(value)
