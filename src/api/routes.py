"""Rotas REST do OrbitFire."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException, Query, Request

from src.api import services
from src.api.schemas import (
    ActiveFiresResponse,
    ErrorResponse,
    HealthResponse,
    RiskMapResponse,
    RiskRankingResponse,
)
from src.config import Settings

router = APIRouter()


def _settings(request: Request) -> Settings:
    """Recupera Settings injetado na aplicacao."""
    return request.app.state.settings


@router.get(
    "/health",
    response_model=HealthResponse,
    responses={500: {"model": ErrorResponse}},
    tags=["operacao"],
)
def health(request: Request) -> HealthResponse:
    """Status da API e contagens do banco."""
    payload = services.get_health(_settings(request))
    return HealthResponse(**payload)


@router.get(
    "/risk/map",
    response_model=RiskMapResponse,
    responses={404: {"model": ErrorResponse}},
    tags=["risco"],
)
def risk_map(
    request: Request,
    reference_date: date | None = Query(default=None),
    band: str | None = Query(default=None),
    uf: str | None = Query(default=None, max_length=2),
) -> RiskMapResponse:
    """Mapa de risco preditivo por celula."""
    if not services.is_valid_band(band):
        raise HTTPException(status_code=422, detail=f"Faixa invalida: {band}")
    try:
        payload = services.get_risk_map(
            _settings(request),
            reference_date=reference_date,
            band=band,
            uf=uf,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return RiskMapResponse(**payload)


@router.get(
    "/risk/ranking",
    response_model=RiskRankingResponse,
    responses={404: {"model": ErrorResponse}},
    tags=["risco"],
)
def risk_ranking(
    request: Request,
    reference_date: date | None = Query(default=None),
    top_n: int = Query(default=10, ge=1, le=100),
) -> RiskRankingResponse:
    """Ranking Top-N de celulas para alocacao de brigadas."""
    try:
        payload = services.get_risk_ranking(
            _settings(request),
            reference_date=reference_date,
            top_n=top_n,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return RiskRankingResponse(**payload)


@router.get(
    "/fires/active",
    response_model=ActiveFiresResponse,
    tags=["focos"],
)
def fires_active(
    request: Request,
    hours: int = Query(default=24, ge=1, le=168),
) -> ActiveFiresResponse:
    """Focos FIRMS detectados na janela horaria."""
    payload = services.get_active_fires(_settings(request), hours=hours)
    return ActiveFiresResponse(**payload)
