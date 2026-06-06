"""Testes da inferencia batch de risco (S3.E3)."""

from dataclasses import replace
from datetime import date, datetime
from pathlib import Path

import pytest

from src.application.calibrate_thresholds import calibrate_thresholds
from src.application.predict_risk import predict_risk
from src.config import BBox, load_settings
from src.domain.cell_id import build_grid_cells
from src.infrastructure.db.repository import open_repository
from src.infrastructure.ml.train import train_model
from test.unit.test_ml_train import _write_sample_dataset


TEST_BBOX = BBox(lat_min=-16.15, lat_max=-15.75, lon_min=-48.30, lon_max=-47.40)
REF_DAY = date(2026, 6, 5)


@pytest.fixture
def predict_settings(tmp_path: Path):
    """Settings com grade, dados operacionais, modelo e thresholds."""
    base = load_settings(env_file=Path("/arquivo/inexistente.env"))
    processed = tmp_path / "processed"
    models = tmp_path / "models"
    processed.mkdir()
    models.mkdir()
    db_path = tmp_path / "orbitfire.db"
    _write_sample_dataset(processed)
    settings = replace(
        base,
        bbox=TEST_BBOX,
        db_path=db_path,
        processed_dir=processed,
        models_dir=models,
    )
    _seed_operational_data(settings)
    train_model(settings)
    calibrate_thresholds(settings)
    return settings


def _seed_operational_data(settings) -> None:
    """Popula grade minima com clima e foco para inferencia."""
    specs = build_grid_cells(settings.bbox, settings.grid_deg)
    repo, session, engine = open_repository(settings.db_path)
    try:
        for spec in specs:
            repo.add_grid_cell(spec.cell_id, spec.lat_center, spec.lon_center, spec.uf)
            repo.add_weather_daily(
                spec.cell_id,
                REF_DAY,
                temp_max=30.0,
                precip_mm=0.0,
                wind_speed=12.0,
            )
        repo.add_fire_event(
            "VIIRS_NRT",
            datetime(2026, 6, 5, 14, 0),
            specs[0].lat_center,
            specs[0].lon_center,
        )
    finally:
        session.close()
        engine.dispose()


def test_predict_risk_persists_scores(predict_settings) -> None:
    """Deve gravar score, faixa e probabilidade por celula."""
    report = predict_risk(predict_settings, reference_date=REF_DAY)

    assert report.reference_date == REF_DAY
    assert report.cell_count > 0
    assert report.scores_written == report.cell_count
    assert sum(report.band_counts.values()) == report.cell_count

    repo, session, engine = open_repository(predict_settings.db_path)
    try:
        rows = repo.list_risk_scores(REF_DAY)
        assert len(rows) == report.cell_count
        sample = rows[0]
        assert 0.0 <= sample.score <= 100.0
        assert sample.band in {"baixo", "medio", "alto", "critico"}
        assert sample.probability is not None
    finally:
        session.close()
        engine.dispose()


def test_predict_risk_upserts_on_rerun(predict_settings) -> None:
    """Segunda execucao deve atualizar scores da mesma data."""
    expected_cells = len(build_grid_cells(predict_settings.bbox, predict_settings.grid_deg))
    predict_risk(predict_settings, reference_date=REF_DAY)
    predict_risk(predict_settings, reference_date=REF_DAY)

    repo, session, engine = open_repository(predict_settings.db_path)
    try:
        assert repo.count_risk_scores() == expected_cells
    finally:
        session.close()
        engine.dispose()


def test_predict_risk_requires_model(predict_settings) -> None:
    """Deve falhar se modelo nao existir."""
    model_path = predict_settings.models_dir / "lgbm_orbitfire.pkl"
    model_path.unlink()
    with pytest.raises(FileNotFoundError, match="train"):
        predict_risk(predict_settings, reference_date=REF_DAY)
