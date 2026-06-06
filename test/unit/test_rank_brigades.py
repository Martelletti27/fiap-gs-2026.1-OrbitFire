"""Testes do ranking Top-N de brigadas (S4.E2)."""

import csv
import json
from dataclasses import replace
from datetime import date, datetime
from pathlib import Path

import pytest

from src.application.predict_risk import predict_risk
from src.application.rank_brigades import rank_brigades
from src.config import load_settings
from src.domain.cell_id import build_grid_cells
from src.infrastructure.db.repository import open_repository
from test.unit.test_predict_risk import predict_settings as _predict_settings_fixture

REF_DAY = date(2026, 6, 5)


@pytest.fixture
def rank_settings(_predict_settings_fixture):
    """Settings com inferencia ja executada."""
    predict_risk(_predict_settings_fixture, reference_date=REF_DAY)
    return _predict_settings_fixture


def test_rank_brigades_exports_json_and_csv(rank_settings) -> None:
    """Deve gerar Top-N com justificativa em JSON e CSV."""
    report = rank_brigades(rank_settings, reference_date=REF_DAY, top_n=3)

    assert report.reference_date == REF_DAY
    assert report.top_n == 3
    assert report.total_candidates > 0
    assert len(report.entries) == 3
    assert report.entries[0].rank == 1
    assert report.json_path.is_file()
    assert report.csv_path.is_file()
    assert report.entries[0].justification.endswith(".")

    payload = json.loads(report.json_path.read_text(encoding="utf-8"))
    assert payload["reference_date"] == REF_DAY.isoformat()
    assert len(payload["entries"]) == 3
    assert "justification" in payload["entries"][0]

    with report.csv_path.open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 3
    assert rows[0]["rank"] == "1"


def test_rank_brigades_requires_risk_scores(tmp_path: Path) -> None:
    """Sem risk_scores o ranking deve falhar com mensagem clara."""
    base = load_settings(env_file=Path("/arquivo/inexistente.env"))
    settings = replace(
        base,
        db_path=tmp_path / "empty.db",
        processed_dir=tmp_path / "processed",
    )
    with pytest.raises(ValueError, match="predict_risk"):
        rank_brigades(settings)


def test_rank_brigades_uses_fire_context_to_boost_priority(rank_settings) -> None:
    """Celula com foco recente deve aparecer no topo do ranking."""
    specs = build_grid_cells(rank_settings.bbox, rank_settings.grid_deg)
    hot_cell = specs[0].cell_id

    repo, session, engine = open_repository(rank_settings.db_path)
    try:
        for offset in range(3):
            repo.add_fire_event(
                "VIIRS_NRT",
                datetime(2026, 6, 5, 10 + offset, 0),
                specs[0].lat_center,
                specs[0].lon_center,
            )
        repo.upsert_risk_score(hot_cell, REF_DAY, score=55.0, band="medio", probability=0.55)
    finally:
        session.close()
        engine.dispose()

    report = rank_brigades(rank_settings, reference_date=REF_DAY, top_n=5)
    top_ids = [entry.cell_id for entry in report.entries]
    assert hot_cell in top_ids
