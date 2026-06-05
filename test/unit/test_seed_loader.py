"""Testes do carregamento de seed offline (S0.E3)."""

from dataclasses import replace
from pathlib import Path

import pytest

from src.config import Settings, load_settings
from src.infrastructure.db.repository import OrbitFireRepository, open_repository
from src.infrastructure.seed.loader import (
    FIRE_SEED_FILE,
    WEATHER_SEED_FILE,
    load_seed_if_offline,
    load_seed_into_db,
)


@pytest.fixture
def seed_dir(tmp_path: Path) -> Path:
    """Copia CSV seed do projeto para diretorio temporario."""
    project_seed = load_settings().seed_dir
    for name in (FIRE_SEED_FILE, WEATHER_SEED_FILE):
        content = (project_seed / name).read_text(encoding="utf-8")
        (tmp_path / name).write_text(content, encoding="utf-8")
    return tmp_path


@pytest.fixture
def memory_repo():
    """Repositorio em memoria isolado por teste."""
    repository, session, engine = open_repository(memory=True)
    yield repository, session, engine
    session.close()
    engine.dispose()


@pytest.fixture
def offline_settings(seed_dir: Path, monkeypatch: pytest.MonkeyPatch) -> Settings:
    """Settings com OFFLINE_MODE e seed em pasta temporaria."""
    monkeypatch.setenv("OFFLINE_MODE", "1")
    base = load_settings(env_file=Path("/arquivo/inexistente.env"))
    return replace(base, seed_dir=seed_dir, offline_mode=True, db_path=seed_dir / "test.db")


def test_load_fire_seed_inserts_rows(
    offline_settings: Settings,
    seed_dir: Path,
    memory_repo: tuple[OrbitFireRepository, object, object],
) -> None:
    """Seed de focos deve popular fire_events."""
    repo, _, _ = memory_repo
    settings = replace(offline_settings, seed_dir=seed_dir)
    result = load_seed_into_db(settings, repo)
    assert result.fires_inserted == 8
    assert result.fires_skipped == 0
    assert repo.count_fire_events() == 8


def test_load_weather_seed_inserts_rows(
    offline_settings: Settings,
    seed_dir: Path,
    memory_repo: tuple[OrbitFireRepository, object, object],
) -> None:
    """Seed de clima deve popular weather_daily."""
    repo, _, _ = memory_repo
    settings = replace(offline_settings, seed_dir=seed_dir)
    result = load_seed_into_db(settings, repo)
    assert result.weather_inserted == 8
    assert result.weather_skipped == 0
    assert repo.count_weather_daily() == 8


def test_seed_load_is_idempotent(
    offline_settings: Settings,
    seed_dir: Path,
    memory_repo: tuple[OrbitFireRepository, object, object],
) -> None:
    """Segunda carga nao deve duplicar registros."""
    repo, _, _ = memory_repo
    settings = replace(offline_settings, seed_dir=seed_dir)
    first = load_seed_into_db(settings, repo)
    second = load_seed_into_db(settings, repo)
    assert first.fires_inserted == 8
    assert second.fires_inserted == 0
    assert second.fires_skipped == 8
    assert repo.count_fire_events() == 8


def test_load_seed_if_offline_skips_when_online(
    seed_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Sem OFFLINE_MODE o loader nao deve persistir seed."""
    monkeypatch.setenv("OFFLINE_MODE", "0")
    settings = replace(
        load_settings(env_file=Path("/arquivo/inexistente.env")),
        seed_dir=seed_dir,
        offline_mode=False,
    )
    assert load_seed_if_offline(settings) is None


def test_load_seed_if_offline_persists_when_enabled(offline_settings, seed_dir) -> None:
    """Com OFFLINE_MODE deve gravar seed no arquivo SQLite informado."""
    settings = replace(offline_settings, db_path=seed_dir / "offline.db")
    result = load_seed_if_offline(settings)
    assert result is not None
    assert result.fires_inserted == 8
    assert result.weather_inserted == 8
    assert (seed_dir / "offline.db").is_file()


def test_missing_seed_file_raises(
    tmp_path: Path,
    memory_repo: tuple[OrbitFireRepository, object, object],
) -> None:
    """Arquivo seed ausente deve gerar erro claro."""
    repo, _, _ = memory_repo
    settings = replace(
        load_settings(env_file=Path("/arquivo/inexistente.env")),
        seed_dir=tmp_path,
    )
    with pytest.raises(FileNotFoundError, match="Seed nao encontrado"):
        load_seed_into_db(settings, repo)
