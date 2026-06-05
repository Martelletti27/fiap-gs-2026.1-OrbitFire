"""Testes de schema SQLite e repositorio (S0.E2)."""

from datetime import date, datetime

import pytest
from sqlalchemy import inspect

from src.infrastructure.db import init_db, open_repository
from src.infrastructure.db.repository import create_engine_for_db

@pytest.fixture
def repo_bundle():
    """Repositorio em memoria isolado por teste."""
    repository, session, engine = open_repository(memory=True)
    yield repository, session, engine
    session.close()
    engine.dispose()


def test_init_db_creates_all_tables(repo_bundle) -> None:
    """Schema deve expor as quatro tabelas do MVP."""
    _, _, engine = repo_bundle
    tables = set(inspect(engine).get_table_names())
    assert tables == {
        "grid_cells",
        "fire_events",
        "weather_daily",
        "risk_scores",
    }


def test_insert_grid_cell(repo_bundle) -> None:
    """Celula da grade persiste com cell_id e coordenadas."""
    repo, _, _ = repo_bundle
    result = repo.add_grid_cell("GO_-16.00_-52.00", -16.0, -52.0, uf="GO")
    assert result.inserted is True
    assert repo.count_grid_cells() == 1


def test_insert_fire_event(repo_bundle) -> None:
    """Foco FIRMS persiste com source e datetime."""
    repo, _, _ = repo_bundle
    when = datetime(2026, 6, 1, 14, 30, 0)
    result = repo.add_fire_event(
        source="VIIRS_NRT",
        acq_datetime=when,
        lat=-15.12345,
        lon=-47.98765,
        confidence=80.0,
        frp=12.5,
    )
    assert result.inserted is True
    assert repo.count_fire_events() == 1


def test_fire_event_dedup(repo_bundle) -> None:
    """Mesma deteccao nao deve ser inserida duas vezes."""
    repo, _, _ = repo_bundle
    when = datetime(2026, 6, 1, 14, 30, 0)
    first = repo.add_fire_event("MODIS_NRT", when, -15.1, -47.9)
    second = repo.add_fire_event("MODIS_NRT", when, -15.1, -47.9)
    assert first.inserted is True
    assert second.inserted is False
    assert repo.count_fire_events() == 1


def test_insert_weather_daily(repo_bundle) -> None:
    """Clima diario persiste por celula e dia."""
    repo, _, _ = repo_bundle
    repo.add_grid_cell("MT_-12.50_-55.00", -12.5, -55.0, uf="MT")
    result = repo.add_weather_daily(
        cell_id="MT_-12.50_-55.00",
        day=date(2026, 6, 1),
        temp_max=32.0,
        temp_min=18.0,
        precip_mm=0.0,
        wind_speed=3.2,
    )
    assert result.inserted is True
    assert repo.count_weather_daily() == 1


def test_insert_risk_score(repo_bundle) -> None:
    """Score preditivo persiste com faixa e data de referencia."""
    repo, _, _ = repo_bundle
    result = repo.add_risk_score(
        cell_id="DF_-15.80_-47.90",
        reference_date=date(2026, 6, 2),
        score=78.5,
        band="alto",
        probability=0.78,
    )
    assert result.inserted is True
    assert repo.count_risk_scores() == 1


def test_risk_score_unique_per_cell_date(repo_bundle) -> None:
    """Uma celula so pode ter um score por data de referencia."""
    repo, _, _ = repo_bundle
    ref = date(2026, 6, 3)
    first = repo.add_risk_score("GO_-16.00_-52.00", ref, 40.0, "medio")
    second = repo.add_risk_score("GO_-16.00_-52.00", ref, 90.0, "critico")
    assert first.inserted is True
    assert second.inserted is False
    assert repo.count_risk_scores() == 1


def test_init_db_idempotent() -> None:
    """Chamar init_db duas vezes nao deve falhar."""
    engine = create_engine_for_db(memory=True)
    init_db(engine)
    init_db(engine)
    tables = inspect(engine).get_table_names()
    assert len(tables) == 4
    engine.dispose()
