"""Testes da configuracao central (S0.E1)."""

from pathlib import Path

import pytest

from src.config import (
    DEFAULT_BBOX,
    FIRMS_NASA_MAP,
    FIRMS_SOURCES,
    GRID_DEG,
    REGION,
    UFS,
    load_settings,
    project_root,
)


def test_region_and_bbox_centro_oeste() -> None:
    """Regiao e bbox devem refletir o Centro-Oeste do Escopo."""
    assert REGION == "Centro-Oeste"
    assert DEFAULT_BBOX.lat_min == pytest.approx(-24.1)
    assert DEFAULT_BBOX.lat_max == pytest.approx(-12.0)
    assert DEFAULT_BBOX.lon_min == pytest.approx(-61.6)
    assert DEFAULT_BBOX.lon_max == pytest.approx(-45.0)


def test_grid_deg_and_ufs() -> None:
    """Grade e UFs confirmadas pelo usuario."""
    assert GRID_DEG == 0.10
    assert UFS == ("GO", "MT", "MS", "DF")


def test_firms_sources_viirs_and_modis() -> None:
    """Ingestao FIRMS deve cobrir VIIRS NRT e MODIS."""
    assert FIRMS_SOURCES == ("VIIRS_NRT", "MODIS_NRT")
    assert set(FIRMS_NASA_MAP) == set(FIRMS_SOURCES)


def test_project_root_contains_src() -> None:
    """Raiz do projeto e a pasta pai de src/."""
    root = project_root()
    assert (root / "src" / "config.py").is_file()


def test_load_settings_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    """Paths de dados devem ficar sob data/ na raiz do projeto."""
    monkeypatch.delenv("DB_PATH", raising=False)
    monkeypatch.setenv("OFFLINE_MODE", "0")
    settings = load_settings(env_file=Path("/arquivo/inexistente.env"))

    assert settings.data_dir == settings.project_root / "data"
    assert settings.raw_firms_dir == settings.data_dir / "raw" / "firms"
    assert settings.raw_weather_dir == settings.data_dir / "raw" / "weather"
    assert settings.processed_dir == settings.data_dir / "processed"
    assert settings.seed_dir == settings.data_dir / "seed"
    assert settings.models_dir == settings.data_dir / "models"
    assert settings.db_path == settings.project_root / "data" / "orbitfire.db"


def test_offline_mode_parsing(monkeypatch: pytest.MonkeyPatch) -> None:
    """OFFLINE_MODE aceita 1/true para demo com seed."""
    monkeypatch.setenv("OFFLINE_MODE", "1")
    settings = load_settings(env_file=Path("/arquivo/inexistente.env"))
    assert settings.offline_mode is True

    monkeypatch.setenv("OFFLINE_MODE", "false")
    settings = load_settings(env_file=Path("/arquivo/inexistente.env"))
    assert settings.offline_mode is False


def test_firms_map_key_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """FIRMS_MAP_KEY vem do ambiente quando definida."""
    monkeypatch.setenv("FIRMS_MAP_KEY", "chave-teste")
    settings = load_settings(env_file=Path("/arquivo/inexistente.env"))
    assert settings.firms_map_key == "chave-teste"


def test_custom_db_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """DB_PATH relativo resolve a partir da raiz do projeto."""
    monkeypatch.setenv("DB_PATH", "data/custom.db")
    settings = load_settings(env_file=Path("/arquivo/inexistente.env"))
    assert settings.db_path == settings.project_root / "data" / "custom.db"
