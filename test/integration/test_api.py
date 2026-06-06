"""Testes de integracao da API FastAPI (S5.E2)."""

from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from src.api.main import create_app
from src.application.predict_risk import predict_risk
from src.config import DEFAULT_BBOX
from src.domain.cell_id import snap_point_to_cell_id
from src.domain.to_boundary import is_in_tocantins
from src.infrastructure.db.repository import open_repository
from test.unit.test_predict_risk import predict_settings as _predict_settings_fixture

REF_DAY = date(2026, 6, 5)

# Coordenada dentro do poligono TO (regiao de Palmas).
TO_LAT = -10.1840
TO_LON = -48.3336


@pytest.fixture
def api_client(_predict_settings_fixture):
    """Cliente HTTP com BD seed e inferencia executada."""
    predict_risk(_predict_settings_fixture, reference_date=REF_DAY)
    app = create_app(_predict_settings_fixture)
    with TestClient(app) as client:
        yield client


def test_health_returns_counts(api_client: TestClient) -> None:
    """GET /health expoe status e contagens basicas."""
    response = api_client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["region"] == "Tocantins"
    assert payload["grid_cells"] > 0
    assert payload["risk_scores"] > 0
    assert payload["reference_date"] == REF_DAY.isoformat()


def test_risk_map_returns_cells(api_client: TestClient) -> None:
    """GET /risk/map lista celulas com score e faixa."""
    response = api_client.get(
        "/risk/map",
        params={"reference_date": REF_DAY.isoformat()},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["reference_date"] == REF_DAY.isoformat()
    assert payload["total_cells"] > 0
    assert len(payload["cells"]) == payload["total_cells"]
    first = payload["cells"][0]
    assert {"cell_id", "lat", "lon", "score", "band"} <= set(first.keys())
    assert sum(payload["band_counts"].values()) == payload["total_cells"]


def test_risk_map_invalid_band_returns_422(api_client: TestClient) -> None:
    """Faixa desconhecida deve retornar 422."""
    response = api_client.get("/risk/map", params={"band": "extremo"})
    assert response.status_code == 422


def test_risk_ranking_returns_top_n(api_client: TestClient) -> None:
    """GET /risk/ranking retorna Top-N com justificativa."""
    response = api_client.get(
        "/risk/ranking",
        params={"reference_date": REF_DAY.isoformat(), "top_n": 3},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["top_n"] == 3
    assert len(payload["entries"]) == 3
    assert payload["entries"][0]["rank"] == 1
    assert payload["entries"][0]["justificativa"]


def test_fires_active_lists_recent_events(api_client: TestClient) -> None:
    """GET /fires/active retorna focos na janela horaria."""
    settings = api_client.app.state.settings
    assert is_in_tocantins(TO_LAT, TO_LON)
    repo, session, engine = open_repository(settings.db_path)
    try:
        repo.add_fire_event(
            "VIIRS_NRT",
            datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=2),
            TO_LAT,
            TO_LON,
        )
    finally:
        session.close()
        engine.dispose()

    response = api_client.get("/fires/active", params={"hours": 24})
    assert response.status_code == 200
    payload = response.json()
    assert payload["hours"] == 24
    assert payload["total"] >= 1
    assert payload["fires"][0]["source"] == "VIIRS_NRT"


def test_fires_summary_returns_aggregations(api_client: TestClient) -> None:
    """GET /fires/summary agrega focos no TO para graficos."""
    settings = api_client.app.state.settings
    cell_id = snap_point_to_cell_id(TO_LAT, TO_LON, DEFAULT_BBOX, settings.grid_deg)
    assert cell_id is not None
    repo, session, engine = open_repository(settings.db_path)
    try:
        repo.add_fire_event(
            "VIIRS_SP",
            datetime(2024, 8, 15, 14, 0, 0),
            TO_LAT,
            TO_LON,
            cell_id=cell_id,
        )
        repo.add_fire_event(
            "MODIS_SP",
            datetime(2024, 8, 16, 10, 0, 0),
            TO_LAT,
            TO_LON,
            cell_id=cell_id,
        )
    finally:
        session.close()
        engine.dispose()

    response = api_client.get("/fires/summary", params={"days": 30})
    assert response.status_code == 200
    payload = response.json()
    assert payload["total_in_region"] >= 2
    assert "VIIRS" in payload["by_source"]
    assert "MODIS" in payload["by_source"]
    assert len(payload["monthly_counts"]) >= 1
    assert len(payload["cell_ranking"]) >= 1
    assert payload["cell_ranking"][0]["rank"] == 1
    assert payload["cell_ranking"][0]["count"] >= 2


def test_risk_map_missing_date_returns_404(api_client: TestClient) -> None:
    """Data sem scores deve retornar 404."""
    response = api_client.get(
        "/risk/map",
        params={"reference_date": "2020-01-01"},
    )
    assert response.status_code == 404
