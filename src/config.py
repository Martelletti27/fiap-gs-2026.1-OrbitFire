"""Configuracao central do OrbitFire: paths, bbox TO e flags de execucao."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

# Tocantins — assets/Escopo.md secao 2 (autorizado 2026-06-05)
REGION = "Tocantins"
UFS: tuple[str, ...] = ("TO",)
GRID_DEG = 0.10

# FIRMS operacional (NRT) — predicao diaria
FIRMS_SOURCES: tuple[str, ...] = ("VIIRS_NRT", "MODIS_NRT")
FIRMS_DAY_RANGE = 5

# FIRMS historico (SP) — treino do modelo
FIRMS_SOURCES_SP: tuple[str, ...] = ("VIIRS_SP", "MODIS_SP")
FIRMS_SP_CHUNK_DAYS = 5
TRAIN_PERIOD_START = date(2024, 6, 1)
TRAIN_PERIOD_END = date(2024, 9, 30)

FIRMS_BASE_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"

# Open-Meteo — clima operacional (forecast) e historico (archive)
OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
OPEN_METEO_TIMEZONE = "America/Sao_Paulo"
WEATHER_DAY_RANGE = 7
WEATHER_FORECAST_DAYS = 1
WEATHER_REQUEST_DELAY_SEC = 1.5
WEATHER_ARCHIVE_MAX_RETRIES = 12
WEATHER_ARCHIVE_RATE_LIMIT_DELAY_SEC = 60.0

# Nomes NASA FIRMS por produto logico
FIRMS_NASA_MAP: dict[str, str] = {
    "VIIRS_NRT": "VIIRS_SNPP_NRT",
    "MODIS_NRT": "MODIS_NRT",
    "VIIRS_SP": "VIIRS_SNPP_SP",
    "MODIS_SP": "MODIS_SP",
}


@dataclass(frozen=True)
class BBox:
    """Retangulo geografico da area de cobertura."""

    lat_min: float
    lat_max: float
    lon_min: float
    lon_max: float

    def contains(self, lat: float, lon: float) -> bool:
        """Indica se o ponto esta dentro do retangulo."""
        return (
            self.lat_min <= lat <= self.lat_max
            and self.lon_min <= lon <= self.lon_max
        )

    def as_firms_area(self) -> str:
        """Formata bbox como west,south,east,north para API NASA FIRMS."""
        return f"{self.lon_min},{self.lat_min},{self.lon_max},{self.lat_max}"


# Bbox aproximado do Tocantins
DEFAULT_BBOX = BBox(lat_min=-13.50, lat_max=-5.20, lon_min=-50.70, lon_max=-45.70)


@dataclass(frozen=True)
class Settings:
    """Parametros resolvidos a partir do ambiente e defaults do projeto."""

    project_root: Path
    region: str
    bbox: BBox
    grid_deg: float
    ufs: tuple[str, ...]
    firms_sources: tuple[str, ...]
    firms_map_key: str
    offline_mode: bool
    db_path: Path
    data_dir: Path
    raw_firms_dir: Path
    raw_weather_dir: Path
    processed_dir: Path
    seed_dir: Path
    models_dir: Path


def project_root() -> Path:
    """Raiz do repositorio (pasta que contem src/)."""
    return Path(__file__).resolve().parent.parent


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def load_settings(env_file: Path | None = None) -> Settings:
    """Carrega .env na raiz (template em src/.env.example) e monta Settings."""
    root = project_root()
    load_dotenv(env_file or root / ".env")

    data_dir = root / "data"
    db_raw = os.getenv("DB_PATH", "data/orbitfire.db")
    db_path = Path(db_raw) if Path(db_raw).is_absolute() else root / db_raw

    return Settings(
        project_root=root,
        region=REGION,
        bbox=DEFAULT_BBOX,
        grid_deg=GRID_DEG,
        ufs=UFS,
        firms_sources=FIRMS_SOURCES,
        firms_map_key=os.getenv("FIRMS_MAP_KEY", ""),
        offline_mode=_env_bool("OFFLINE_MODE", False),
        db_path=db_path,
        data_dir=data_dir,
        raw_firms_dir=data_dir / "raw" / "firms",
        raw_weather_dir=data_dir / "raw" / "weather",
        processed_dir=data_dir / "processed",
        seed_dir=data_dir / "seed",
        models_dir=data_dir / "models",
    )


def ensure_data_dirs(settings: Settings) -> None:
    """Cria pastas de dados se ainda nao existirem."""
    for path in (
        settings.raw_firms_dir,
        settings.raw_weather_dir,
        settings.processed_dir,
        settings.seed_dir,
        settings.models_dir,
    ):
        path.mkdir(parents=True, exist_ok=True)
