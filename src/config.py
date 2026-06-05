"""Configuracao central do OrbitFire: paths, bbox Centro-Oeste e flags de execucao."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Centro-Oeste — GO, MT, MS, DF (docs/Escopo.md secao 2)
REGION = "Centro-Oeste"
UFS: tuple[str, ...] = ("GO", "MT", "MS", "DF")
GRID_DEG = 0.10

# Produtos FIRMS ativos na ingestao (VIIRS e MODIS)
FIRMS_SOURCES: tuple[str, ...] = ("VIIRS_NRT", "MODIS_NRT")
FIRMS_BASE_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"
FIRMS_DAY_RANGE = 5

# Open-Meteo — clima diario sem API key
OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_TIMEZONE = "America/Sao_Paulo"
WEATHER_DAY_RANGE = 7

# Nomes de arquivo NASA FIRMS por produto logico (S1)
FIRMS_NASA_MAP: dict[str, str] = {
    "VIIRS_NRT": "VIIRS_SNPP_NRT",
    "MODIS_NRT": "MODIS_NRT",
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


# Bbox aproximado do Centro-Oeste
DEFAULT_BBOX = BBox(lat_min=-24.1, lat_max=-12.0, lon_min=-61.6, lon_max=-45.0)


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
