"""Testes do job de ingestao FIRMS (S1.E1)."""

from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import pytest

from src.config import DEFAULT_BBOX, load_settings
from src.infrastructure.db.repository import open_repository
from src.infrastructure.firms.ingest import run_firms_ingest

NASA_CSV = """latitude,longitude,brightness,scan,track,acq_date,acq_time,satellite,instrument,confidence,version,bright_t31,frp,daynight
-10.05,-47.92,320.5,0.5,0.5,2026-06-01,1430,N,VIIRS,85,nrt,285.2,18.4,D
-8.20,-48.30,310.0,0.5,0.5,2026-06-02,1605,N,VIIRS,90,nrt,280.0,31.5,D
"""


@pytest.fixture
def online_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Settings online com BD e raw em pasta temporaria."""
    monkeypatch.setenv("OFFLINE_MODE", "0")
    monkeypatch.setenv("FIRMS_MAP_KEY", "chave-teste")
    base = load_settings(env_file=Path("/arquivo/inexistente.env"))
    return replace(
        base,
        offline_mode=False,
        firms_map_key="chave-teste",
        db_path=tmp_path / "orbitfire.db",
        raw_firms_dir=tmp_path / "raw" / "firms",
    )


def test_run_firms_ingest_online_persists_and_saves_raw(online_settings) -> None:
    """Ingestao online deve gravar raw e popular fire_events."""
    with patch(
        "src.infrastructure.firms.ingest.FirmsAreaClient.fetch_area_csv",
        return_value=NASA_CSV,
    ):
        results = run_firms_ingest(online_settings)

    assert len(results) == 2
    viirs = next(item for item in results if item.source == "VIIRS_NRT")
    assert viirs.fetched == 2
    assert viirs.inserted == 2
    assert viirs.skipped == 0
    assert viirs.raw_path is not None
    assert viirs.raw_path.is_file()

    modis = next(item for item in results if item.source == "MODIS_NRT")
    assert modis.inserted == 2

    repo, session, engine = open_repository(online_settings.db_path)
    try:
        # VIIRS e MODIS recebem o mesmo CSV mock (4 deteccoes no total)
        assert repo.count_fire_events() == 4
    finally:
        session.close()
        engine.dispose()


def test_run_firms_ingest_online_is_idempotent(online_settings) -> None:
    """Segunda ingestao deve ignorar duplicatas."""
    with patch(
        "src.infrastructure.firms.ingest.FirmsAreaClient.fetch_area_csv",
        return_value=NASA_CSV,
    ):
        first = run_firms_ingest(online_settings)
        second = run_firms_ingest(online_settings)

    viirs_second = next(item for item in second if item.source == "VIIRS_NRT")
    assert first[0].inserted == 2
    assert viirs_second.inserted == 0
    assert viirs_second.skipped == 2


def test_run_firms_ingest_offline_delegates_seed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """OFFLINE_MODE deve usar seed em vez da API."""
    monkeypatch.setenv("OFFLINE_MODE", "1")
    project_seed = load_settings().seed_dir
    seed_dir = tmp_path / "seed"
    seed_dir.mkdir()
    for name in ("fire_events_seed.csv", "weather_daily_seed.csv"):
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
    results = run_firms_ingest(settings)
    assert len(results) == 1
    assert results[0].source == "OFFLINE_SEED"
    assert results[0].inserted == 8


def test_run_firms_ingest_requires_map_key_online(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Sem MAP_KEY o modo online deve falhar."""
    monkeypatch.setenv("OFFLINE_MODE", "0")
    monkeypatch.delenv("FIRMS_MAP_KEY", raising=False)
    settings = replace(
        load_settings(env_file=Path("/arquivo/inexistente.env")),
        offline_mode=False,
        firms_map_key="",
        db_path=tmp_path / "orbitfire.db",
    )
    with pytest.raises(ValueError, match="FIRMS_MAP_KEY"):
        run_firms_ingest(settings)
