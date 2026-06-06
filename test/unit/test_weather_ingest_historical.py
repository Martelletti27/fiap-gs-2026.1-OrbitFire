"""Testes da ingestao historica de clima resiliente."""

from dataclasses import replace
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

from src.config import TRAIN_PERIOD_START, TRAIN_PERIOD_END, load_settings
from src.infrastructure.db.repository import open_repository
from src.infrastructure.weather.ingest_historical import (
    _print_progress,
    run_weather_historical_ingest,
    summarize_historical,
)

SAMPLE_PAYLOAD = {
    "daily": {
        "time": ["2024-06-01", "2024-06-02"],
        "temperature_2m_max": [30.0, 31.0],
        "temperature_2m_min": [18.0, 19.0],
        "precipitation_sum": [0.0, 1.0],
        "wind_speed_10m_max": [10.0, 11.0],
    }
}


@pytest.fixture
def historical_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Settings online com grade minima para ingestao historica."""
    monkeypatch.setenv("OFFLINE_MODE", "0")
    base = load_settings(env_file=Path("/arquivo/inexistente.env"))
    db_path = tmp_path / "orbitfire.db"
    repo, session, engine = open_repository(db_path)
    try:
        repo.add_grid_cell("TO_-10.20_-48.30", -10.2, -48.3, uf="TO")
        repo.add_grid_cell("TO_-10.20_-48.40", -10.2, -48.4, uf="TO")
    finally:
        session.close()
        engine.dispose()
    return replace(
        base,
        offline_mode=False,
        db_path=db_path,
        raw_weather_dir=tmp_path / "raw" / "weather",
    )


def test_run_weather_historical_ingest_continues_after_cell_failure(
    historical_settings,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Falha em uma celula nao deve derrubar a ingestao das demais."""
    ok_target = MagicMock()
    ok_target.cell_id = "TO_-10.20_-48.30"
    ok_target.lat = -10.2
    ok_target.lon = -48.3
    fail_target = MagicMock()
    fail_target.cell_id = "TO_-10.20_-48.40"
    fail_target.lat = -10.2
    fail_target.lon = -48.4

    def fake_fetch(lat, lon, *, start_date, end_date):
        if lon == -48.4:
            raise requests.HTTPError("429")
        return SAMPLE_PAYLOAD

    with (
        patch(
            "src.infrastructure.weather.ingest_historical.resolve_weather_targets",
            return_value=[ok_target, fail_target],
        ),
        patch(
            "src.infrastructure.weather.ingest_historical.OpenMeteoClient.fetch_historical_daily",
            side_effect=fake_fetch,
        ),
        patch(
            "src.infrastructure.weather.ingest_historical.WEATHER_REQUEST_DELAY_SEC",
            0,
        ),
    ):
        results = run_weather_historical_ingest(historical_settings)

    assert len(results) == 2
    assert results[0].failed is False
    assert results[0].inserted == 2
    assert results[1].failed is True
    output = capsys.readouterr().out
    assert "Progresso clima:" in output


def test_summarize_historical_reports_pending() -> None:
    """Resumo deve expor completas, falhas e pendentes."""
    from src.infrastructure.weather.ingest import WeatherIngestResult

    results = [
        WeatherIngestResult("A", fetched=2, inserted=2, skipped=0),
        WeatherIngestResult("B", fetched=0, inserted=0, skipped=0, failed=True),
    ]
    summary = summarize_historical(results, total_cells=4, complete_cells=2)
    assert summary.complete == 2
    assert summary.failed == 1
    assert summary.pending == 2


def test_print_progress_format(capsys: pytest.CaptureFixture[str]) -> None:
    """Progresso deve mostrar contagem e percentual."""
    _print_progress(2869, 4150)
    assert capsys.readouterr().out.strip() == "Progresso clima: 2869/4150 (69.1%)"
