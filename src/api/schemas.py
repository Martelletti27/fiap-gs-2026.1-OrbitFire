"""Schemas Pydantic dos endpoints REST."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

RiskBand = Literal["baixo", "medio", "alto", "critico"]


class HealthResponse(BaseModel):
    """Status operacional da API e do banco."""

    status: Literal["ok", "degraded"]
    region: str
    offline_mode: bool
    grid_cells: int
    risk_scores: int
    fire_events: int
    reference_date: date | None = None


class RiskMapCell(BaseModel):
    """Celula com score de risco para o mapa."""

    cell_id: str
    lat: float
    lon: float
    score: float
    band: RiskBand
    uf: str | None = None


class RiskMapResponse(BaseModel):
    """Mapa de risco preditivo por celula."""

    reference_date: date
    total_cells: int
    band_counts: dict[str, int]
    cells: list[RiskMapCell]


class RankingEntry(BaseModel):
    """Linha do ranking de brigadas."""

    rank: int
    cell_id: str
    lat: float
    lon: float
    priority_score: float
    risk_score: float
    band: RiskBand
    justificativa: str


class RiskRankingResponse(BaseModel):
    """Top-N de celulas prioritarias."""

    reference_date: date
    top_n: int
    total_candidates: int
    entries: list[RankingEntry]


class ActiveFire(BaseModel):
    """Foco FIRMS recente para overlay no mapa."""

    lat: float
    lon: float
    acq_datetime: datetime
    source: str
    frp: float | None = None
    cell_id: str | None = None


class ActiveFiresResponse(BaseModel):
    """Focos ativos no periodo consultado."""

    hours: int
    total: int
    fires: list[ActiveFire]


class ErrorResponse(BaseModel):
    """Corpo padrao de erro."""

    detail: str = Field(..., examples=["Recurso nao encontrado"])
