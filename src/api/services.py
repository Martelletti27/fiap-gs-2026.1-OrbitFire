"""Consultas de leitura para os endpoints REST."""

from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timedelta, timezone

from src.application.rank_brigades import build_brigade_ranking
from src.config import Settings
from src.domain.cell_id import parse_cell_center, snap_point_to_cell_id
from src.domain.risk_score import RISK_BANDS
from src.domain.to_boundary import is_in_tocantins
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
    """Lista focos FIRMS dentro da janela horaria no Tocantins."""
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
            and is_in_tocantins(event.lat, event.lon)
        ]
    return {"hours": hours, "total": len(fires), "fires": fires}


def get_fires_summary(
    settings: Settings,
    *,
    days: int = 30,
    top_cells: int = 15,
) -> dict[str, object]:
    """Agrega focos no TO para graficos de comportamento regional."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    daily_cutoff = (now - timedelta(days=days)).date()
    with repository_session(settings.db_path) as repository:
        daily_counter: Counter[date] = Counter()
        source_counter: Counter[str] = Counter()
        monthly_counter: Counter[str] = Counter()
        cell_counter: Counter[str] = Counter()
        grid_by_id = {cell.cell_id: cell for cell in repository.list_grid_cells()}
        total_in_region = 0

        for event in repository.list_fire_events():
            if not is_in_tocantins(event.lat, event.lon):
                continue
            total_in_region += 1
            day = event.acq_datetime.date()
            source_counter[_normalize_fire_source(event.source)] += 1
            monthly_counter[day.strftime("%Y-%m")] += 1
            if day >= daily_cutoff:
                daily_counter[day] += 1
            cell_id = _resolve_fire_cell_id(event, settings)
            if cell_id is not None:
                cell_counter[cell_id] += 1

    daily_counts = _fill_daily_series(daily_cutoff, now.date(), daily_counter)
    monthly_counts = [
        {"month": month, "count": monthly_counter[month]}
        for month in sorted(monthly_counter)
    ][-6:]
    cell_ranking = _build_cell_ranking(cell_counter, grid_by_id, top_cells=top_cells)

    return {
        "days": days,
        "total_in_region": total_in_region,
        "daily_counts": daily_counts,
        "by_source": dict(source_counter),
        "monthly_counts": monthly_counts,
        "cell_ranking": cell_ranking,
    }


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


def _normalize_fire_source(source: str) -> str:
    """Agrupa produtos FIRMS em rotulos legiveis para graficos."""
    upper = source.upper()
    if "VIIRS" in upper:
        return "VIIRS"
    if "MODIS" in upper:
        return "MODIS"
    return source


def _resolve_fire_cell_id(event: object, settings: Settings) -> str | None:
    """Obtem cell_id do foco ou infere pela coordenada na grade."""
    cell_id = getattr(event, "cell_id", None)
    if cell_id:
        return str(cell_id)
    lat = float(getattr(event, "lat"))
    lon = float(getattr(event, "lon"))
    return snap_point_to_cell_id(lat, lon, settings.bbox, settings.grid_deg)


def _build_cell_ranking(
    cell_counter: Counter[str],
    grid_by_id: dict[str, object],
    *,
    top_cells: int,
) -> list[dict[str, object]]:
    """Monta Top-N de quadrantes com mais focos historicos."""
    ranking: list[dict[str, object]] = []
    for rank, (cell_id, count) in enumerate(
        cell_counter.most_common(top_cells),
        start=1,
    ):
        grid_cell = grid_by_id.get(cell_id)
        if grid_cell is not None:
            lat = float(grid_cell.lat_center)
            lon = float(grid_cell.lon_center)
        else:
            lat, lon = parse_cell_center(cell_id)
        ranking.append(
            {
                "rank": rank,
                "cell_id": cell_id,
                "lat": lat,
                "lon": lon,
                "count": count,
            }
        )
    return ranking


def _fill_daily_series(
    start: date,
    end: date,
    counter: Counter[date],
) -> list[dict[str, object]]:
    """Preenche dias sem foco com zero para serie temporal continua."""
    series: list[dict[str, object]] = []
    current = start
    while current <= end:
        series.append({"day": current, "count": counter.get(current, 0)})
        current += timedelta(days=1)
    return series
