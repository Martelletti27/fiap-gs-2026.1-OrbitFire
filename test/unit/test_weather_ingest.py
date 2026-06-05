"""Testes do job de ingestao de clima (S1.E2)."""

from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import pytest

from src.config import load_settings
from src.infrastructure.db.repository import open_repository
from src.infrastructure.seed.loader import WEATHER_SEED_FILE
from src.infrastructure.weather.ingest import run_weather_ingest

SAMPLE_PAYLOAD = {
    "daily": {
        "time": ["2026-06-01", "2026-06-02"],
        "temperature_2m_max": [29.5, 30.1],
        "temperature_2m_min": [18.2, 17.9],
        "precipitation_sum": [0.0, 1.2],
        "wind_speed_10m_max": [2.8, 3.1],
    }
}


@pytest.fixture
def online_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Settings online com seed e paths temporarios."""
    monkeypatch.setenv("OFFLINE_MODE", "0")
    project_seed = load_settings().seed_dir
    seed_dir = tmp_path / "seed"
    seed_dir.mkdir()
    (seed_dir / WEATHER_SEED_FILE).write_text(
        (project_seed / WEATHER_SEED_FILE).read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    base = load_settings(env_file=Path("/arquivo/inexistente.env"))
    return replace(
        base,
        offline_mode=False,
        seed_dir=seed_dir,
        db_path=tmp_path / "orbitfire.db",
        raw_weather_dir=tmp_path / "raw" / "weather",
    )


def test_run_weather_ingest_online_persists(online_settings) -> None:
    """Ingestao online deve gravar raw e popular weather_daily."""
    with patch(
        "src.infrastructure.weather.ingest.OpenMeteoClient.fetch_daily",
        return_value=SAMPLE_PAYLOAD,
    ):
        results = run_weather_ingest(online_settings)

    assert len(results) == 6
    total_inserted = sum(item.inserted for item in results)
    assert total_inserted == 12
    assert all(item.raw_path is not None for item in results)

    repo, session, engine = open_repository(online_settings.db_path)
    try:
        assert repo.count_weather_daily() == 12
    finally:
        session.close()
        engine.dispose()


def test_run_weather_ingest_online_is_idempotent(online_settings) -> None:
    """Segunda ingestao deve ignorar duplicatas."""
    with patch(
        "src.infrastructure.weather.ingest.OpenMeteoClient.fetch_daily",
        return_value=SAMPLE_PAYLOAD,
    ):
        first = run_weather_ingest(online_settings)
        second = run_weather_ingest(online_settings)

    assert sum(item.inserted for item in first) == 12
    assert sum(item.inserted for item in second) == 0
    assert sum(item.skipped for item in second) == 12


def test_run_weather_ingest_offline_delegates_seed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """OFFLINE_MODE deve usar seed de clima."""
    monkeypatch.setenv("OFFLINE_MODE", "1")
    project_seed = load_settings().seed_dir
    seed_dir = tmp_path / "seed"
    seed_dir.mkdir()
    for name in ("fire_events_seed.csv", WEATHER_SEED_FILE):
        (seed_dir / name).write_text(
            (project_seed / name).read_text(encoding="utf-8"),
            encoding="utf-8",
        )

    settings = replace(
        load_settings(env_file=Path("/arquivo/inexistente.env")),
        offline_mode=True,
        seed_dir=seed_dir,
        db_path=tmp_path / "offline.db",
    )
    results = run_weather_ingest(settings)
    assert len(results) == 1
    assert results[0].cell_id == "OFFLINE_SEED"
    assert results[0].inserted == 8
