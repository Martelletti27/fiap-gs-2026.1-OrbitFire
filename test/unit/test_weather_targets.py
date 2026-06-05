"""Testes de resolucao de alvos de clima (S1.E2)."""

from dataclasses import replace
from pathlib import Path

import pytest

from src.config import load_settings
from src.infrastructure.db.repository import open_repository
from src.infrastructure.seed.loader import WEATHER_SEED_FILE
from src.domain.cell_id import parse_cell_center
from src.infrastructure.weather.targets import resolve_weather_targets


def test_parse_cell_center_from_seed_format() -> None:
    """cell_id UF_lat_lon deve expor coordenadas centrais."""
    lat, lon = parse_cell_center("DF_-15.80_-47.90")
    assert lat == pytest.approx(-15.80)
    assert lon == pytest.approx(-47.90)


def test_resolve_targets_from_seed_when_grid_empty(tmp_path: Path) -> None:
    """Sem grade no BD, usa cell_ids unicos do seed."""
    seed_dir = tmp_path / "seed"
    seed_dir.mkdir()
    content = (load_settings().seed_dir / WEATHER_SEED_FILE).read_text(encoding="utf-8")
    (seed_dir / WEATHER_SEED_FILE).write_text(content, encoding="utf-8")

    repo, session, engine = open_repository(memory=True)
    try:
        settings = replace(load_settings(), seed_dir=seed_dir)
        targets = resolve_weather_targets(settings, repo)
        assert len(targets) == 6
        assert targets[0].cell_id.startswith(("DF_", "GO_", "MT_", "MS_"))
    finally:
        session.close()
        engine.dispose()


def test_resolve_targets_from_grid_cells() -> None:
    """Com grade persistida, prioriza celulas do SQLite."""
    repo, session, engine = open_repository(memory=True)
    try:
        repo.add_grid_cell("GO_-16.00_-49.10", -16.0, -49.1, uf="GO")
        repo.add_grid_cell("MT_-12.50_-55.10", -12.5, -55.1, uf="MT")
        settings = load_settings(env_file=Path("/arquivo/inexistente.env"))
        targets = resolve_weather_targets(settings, repo)
        assert len(targets) == 2
        assert targets[0].lat == pytest.approx(-16.0)
    finally:
        session.close()
        engine.dispose()
