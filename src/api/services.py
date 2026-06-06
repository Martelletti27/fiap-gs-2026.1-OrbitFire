"""Consultas de leitura para os endpoints REST."""

from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timedelta, timezone

from src.application.rank_brigades import build_brigade_ranking
from src.config import Settings
from src.domain.risk_score import RISK_BANDS
from src.infrastructure.db.repository import OrbitFireRepository, repository_session


def get_health(settings: Settings) -> dict[str, object]:
    """Monta payload de saude com contagens e data de referencia."""
    with repository_session(settings.db_path) as repository:
        scores = repository.list_risk_scores()
        reference_date = (
            max(row.reference_date for row in scores) if scores else None
        )
        grid_cells = repository.count_grid_cells()
        return {
            "status": "ok" if scores and grid_cells else "degraded",
            "region": settings.region,
            "offline_mode": settings.offline_mode,
            "grid_cells": grid_cells,
            "risk_scores": len(scores),
            "fire_events": repository.count_fire_events(),
            "reference_date": reference_date,
        }


def get_risk_map(
    settings: Settings,
    *,
    reference_date: date | None = None,
    band: str | None = None,
    uf: str | None = None,
) -> dict[str, object]:
    """Lista scores por celula com coordenadas para o mapa."""
    with repository_session(settings.db_path) as repository:
        ref_day = _resolve_reference_date(repository, reference_date)
        grid_by_id = {cell.cell_id: cell for cell in repository.list_grid_cells()}
        rows = [
            row
            for row in repository.list_risk_scores(ref_day)
            if row.reference_date == ref_day
        ]
        if not rows:
            raise LookupError(f"Sem risk_scores para {ref_day.isoformat()}")

        cells: list[dict[str, object]] = []
        band_counter: Counter[str] = Counter()
        for row in rows:
            if band is not None and row.band != band:
                continue
            grid_cell = grid_by_id.get(row.cell_id)
            cell_uf = grid_cell.uf if grid_cell else None
            if uf is not None and cell_uf != uf:
                continue
            lat = grid_cell.lat_center if grid_cell else 0.0
            lon = grid_cell.lon_center if grid_cell else 0.0
            cells.append(
                {
                    "cell_id": row.cell_id,
                    "lat": lat,
                    "lon": lon,
                    "score": row.score,
                    "band": row.band,
                    "uf": cell_uf,
                }
            )
            band_counter[row.band] += 1

        if band is None and uf is None:
            counts = dict(band_counter)
        else:
            counts = dict(Counter(item["band"] for item in cells))

        return {
            "reference_date": ref_day,
            "total_cells": len(cells),
            "band_counts": counts,
            "cells": cells,
        }


def get_risk_ranking(
    settings: Settings,
    *,
    reference_date: date | None = None,
    top_n: int = 10,
) -> dict[str, object]:
    """Retorna Top-N com justificativa operacional."""
    result = build_brigade_ranking(
        settings,
        reference_date=reference_date,
        top_n=top_n,
    )
    return {
        "reference_date": result.reference_date,
        "top_n": result.top_n,
        "total_candidates": result.total_candidates,
        "entries": [
            {
                "rank": entry.rank,
                "cell_id": entry.cell_id,
                "lat": entry.lat_center,
                "lon": entry.lon_center,
                "priority_score": entry.priority_score,
                "risk_score": entry.risk_score,
                "band": entry.band,
                "justificativa": entry.justification,
            }
            for entry in result.entries
        ],
    }


def get_active_fires(settings: Settings, *, hours: int = 24) -> dict[str, object]:
    """Lista focos FIRMS dentro da janela horaria."""
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=hours)
    with repository_session(settings.db_path) as repository:
        fires = [
            {
                "lat": event.lat,
                "lon": event.lon,
                "acq_datetime": _as_utc(event.acq_datetime),
                "source": event.source,
                "frp": event.frp,
                "cell_id": event.cell_id,
            }
            for event in repository.list_fire_events()
            if event.acq_datetime >= cutoff
        ]
    return {"hours": hours, "total": len(fires), "fires": fires}


def _resolve_reference_date(
    repository: OrbitFireRepository,
    reference_date: date | None,
) -> date:
    """Obtem data de referencia dos scores ou valida parametro."""
    if reference_date is not None:
        return reference_date
    scores = repository.list_risk_scores()
    if not scores:
        raise LookupError(
            "Sem risk_scores no banco. Execute python -m src.application.predict_risk"
        )
    return max(row.reference_date for row in scores)


def _as_utc(value: datetime) -> datetime:
    """Normaliza datetime naive como UTC para serializacao ISO."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def is_valid_band(value: str | None) -> bool:
    """Indica se faixa informada e valida."""
    return value is None or value in RISK_BANDS
