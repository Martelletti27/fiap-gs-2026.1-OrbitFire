"""Carrega CSV seed em SQLite quando OFFLINE_MODE esta ativo."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from src.config import Settings, load_settings
from src.infrastructure.db.repository import OrbitFireRepository, persist_many, repository_session

FIRE_SEED_FILE = "fire_events_seed.csv"
WEATHER_SEED_FILE = "weather_daily_seed.csv"


@dataclass(frozen=True)
class SeedLoadResult:
    """Contagem de linhas inseridas ou ignoradas por deduplicacao."""

    fires_inserted: int
    fires_skipped: int
    weather_inserted: int
    weather_skipped: int


def load_weather_seed_if_offline(settings: Settings | None = None) -> tuple[int, int] | None:
    """Persiste somente clima do seed quando OFFLINE_MODE; retorna None se online."""
    cfg = settings or load_settings()
    if not cfg.offline_mode:
        return None

    with repository_session(cfg.db_path) as repository:
        return _load_weather_seed(cfg.seed_dir / WEATHER_SEED_FILE, repository)


def load_seed_if_offline(settings: Settings | None = None) -> SeedLoadResult | None:
    """Persiste seed no BD somente com OFFLINE_MODE; retorna None se modo online."""
    cfg = settings or load_settings()
    if not cfg.offline_mode:
        return None

    with repository_session(cfg.db_path) as repository:
        return load_seed_into_db(cfg, repository)


def load_seed_into_db(settings: Settings, repository: OrbitFireRepository) -> SeedLoadResult:
    """Le CSV de data/seed/ e persiste focos e clima."""
    fires = _load_fire_seed(settings.seed_dir / FIRE_SEED_FILE, repository)
    weather = _load_weather_seed(settings.seed_dir / WEATHER_SEED_FILE, repository)
    return SeedLoadResult(
        fires_inserted=fires[0],
        fires_skipped=fires[1],
        weather_inserted=weather[0],
        weather_skipped=weather[1],
    )


def _load_fire_seed(path: Path, repository: OrbitFireRepository) -> tuple[int, int]:
    """Importa focos FIRMS do CSV seed."""
    return persist_many(
        _read_csv(path),
        lambda row: repository.add_fire_event(
            source=row["source"],
            acq_datetime=datetime.fromisoformat(row["acq_datetime"]),
            lat=float(row["lat"]),
            lon=float(row["lon"]),
            confidence=_optional_float(row.get("confidence")),
            frp=_optional_float(row.get("frp")),
            cell_id=row.get("cell_id") or None,
        ),
    )


def _load_weather_seed(path: Path, repository: OrbitFireRepository) -> tuple[int, int]:
    """Importa clima diario do CSV seed."""
    return persist_many(
        _read_csv(path),
        lambda row: repository.add_weather_daily(
            cell_id=row["cell_id"],
            day=date.fromisoformat(row["day"]),
            temp_max=_optional_float(row.get("temp_max")),
            temp_min=_optional_float(row.get("temp_min")),
            precip_mm=_optional_float(row.get("precip_mm")),
            wind_speed=_optional_float(row.get("wind_speed")),
        ),
    )


def _read_csv(path: Path) -> list[dict[str, str]]:
    """Le CSV com cabecalho; falha se arquivo nao existir."""
    if not path.is_file():
        raise FileNotFoundError(f"Seed nao encontrado: {path}")
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _optional_float(value: str | None) -> float | None:
    """Converte campo CSV vazio em None."""
    if value is None or value.strip() == "":
        return None
    return float(value)
