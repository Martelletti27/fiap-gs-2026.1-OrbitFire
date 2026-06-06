"""Caso de uso: ranking Top-N de celulas para alocacao de brigadas."""

from __future__ import annotations

import csv
import json
import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from src.application.db_loaders import load_fire_points, load_weather_points
from src.config import Settings, ensure_data_dirs, load_settings
from src.domain.cell_id import parse_cell_center
from src.domain.features import build_features_table
from src.domain.prioritization import (
    PrioritizationCandidate,
    PrioritizedCell,
    build_justification,
    rank_priorities,
)
from src.infrastructure.db.repository import OrbitFireRepository, repository_session
from src.infrastructure.db.schema import GridCell, RiskScore

logger = logging.getLogger(__name__)

DEFAULT_TOP_N = 10
BRIGADE_RANKING_JSON = "brigade_ranking.json"
BRIGADE_RANKING_CSV = "brigade_ranking.csv"


@dataclass(frozen=True)
class BrigadeRankEntry:
    """Linha do ranking exportado com coordenadas e justificativa."""

    rank: int
    cell_id: str
    lat_center: float
    lon_center: float
    priority_score: float
    risk_score: float
    band: str
    fires_1d: int
    fires_7d: int
    neighbor_fires_7d: int
    justification: str


@dataclass(frozen=True)
class BrigadeRankingResult:
    """Ranking calculado sem exportar arquivos (API e jobs)."""

    reference_date: date
    top_n: int
    total_candidates: int
    entries: list[BrigadeRankEntry]


@dataclass(frozen=True)
class BrigadeRankingReport:
    """Resumo do ranking persistido em JSON e CSV."""

    reference_date: date
    top_n: int
    total_candidates: int
    entries: list[BrigadeRankEntry]
    json_path: Path
    csv_path: Path


def build_brigade_ranking(
    settings: Settings | None = None,
    *,
    reference_date: date | None = None,
    top_n: int = DEFAULT_TOP_N,
) -> BrigadeRankingResult:
    """Ranqueia celulas a partir de risk_scores sem gravar export."""
    cfg = settings or load_settings()

    with repository_session(cfg.db_path) as repository:
        ref_day, entries, total = _compute_ranking(
            repository,
            cfg,
            reference_date=reference_date,
            top_n=top_n,
        )

    return BrigadeRankingResult(
        reference_date=ref_day,
        top_n=top_n,
        total_candidates=total,
        entries=entries,
    )


def rank_brigades(
    settings: Settings | None = None,
    *,
    reference_date: date | None = None,
    top_n: int = DEFAULT_TOP_N,
) -> BrigadeRankingReport:
    """Ranqueia celulas a partir de risk_scores e exporta JSON/CSV em processed/."""
    cfg = settings or load_settings()
    ensure_data_dirs(cfg)
    result = build_brigade_ranking(
        cfg,
        reference_date=reference_date,
        top_n=top_n,
    )

    json_path, csv_path = _export_ranking(
        cfg.processed_dir,
        result.reference_date,
        result.top_n,
        result.entries,
    )
    logger.info(
        "Ranking brigadas: ref=%s top_n=%s candidates=%s json=%s",
        result.reference_date,
        result.top_n,
        result.total_candidates,
        json_path,
    )
    return BrigadeRankingReport(
        reference_date=result.reference_date,
        top_n=result.top_n,
        total_candidates=result.total_candidates,
        entries=result.entries,
        json_path=json_path,
        csv_path=csv_path,
    )


def _compute_ranking(
    repository: OrbitFireRepository,
    cfg: Settings,
    *,
    reference_date: date | None,
    top_n: int,
) -> tuple[date, list[BrigadeRankEntry], int]:
    """Monta ranking em memoria a partir do repositorio."""
    risk_rows = repository.list_risk_scores(reference_date)
    if not risk_rows:
        hint = "Execute python -m src.application.predict_risk antes do ranking"
        if reference_date is not None:
            raise ValueError(
                f"Sem risk_scores para {reference_date.isoformat()}. {hint}"
            )
        raise ValueError(f"Sem risk_scores no banco. {hint}")

    ref_day = reference_date or max(row.reference_date for row in risk_rows)
    risk_rows = [row for row in risk_rows if row.reference_date == ref_day]
    if not risk_rows:
        raise ValueError(f"Sem risk_scores para {ref_day.isoformat()}")

    grid_by_id = {cell.cell_id: cell for cell in repository.list_grid_cells()}
    fires = load_fire_points(repository, cfg.bbox, cfg.grid_deg)
    weather = load_weather_points(repository)
    cell_ids = [row.cell_id for row in risk_rows]
    feature_by_cell = _feature_index(
        cell_ids,
        ref_day,
        fires,
        weather,
        cfg.grid_deg,
    )
    candidates = _build_candidates(risk_rows, feature_by_cell)
    ranked = rank_priorities(candidates, top_n=top_n)
    entries = _to_entries(ranked, candidates, grid_by_id)
    return ref_day, entries, len(candidates)


def _feature_index(
    cell_ids: list[str],
    reference_date: date,
    fires,
    weather,
    grid_deg: float,
) -> dict[str, object]:
    """Indexa features de inferencia por cell_id na data de referencia."""
    rows = build_features_table(
        cell_ids,
        [reference_date],
        fires,
        weather,
        grid_deg=grid_deg,
    )
    return {row.cell_id: row for row in rows}


def _build_candidates(
    risk_rows: list[RiskScore],
    feature_by_cell: dict[str, object],
) -> list[PrioritizationCandidate]:
    """Monta candidatos combinando score persistido e features de focos."""
    candidates: list[PrioritizationCandidate] = []
    for row in risk_rows:
        features = feature_by_cell.get(row.cell_id)
        fires_1d = getattr(features, "fires_1d", 0) if features else 0
        fires_7d = getattr(features, "fires_7d", 0) if features else 0
        neighbor = getattr(features, "neighbor_fires_7d", 0) if features else 0
        candidates.append(
            PrioritizationCandidate(
                cell_id=row.cell_id,
                risk_score=row.score,
                band=row.band,
                fires_1d=fires_1d,
                fires_7d=fires_7d,
                neighbor_fires_7d=neighbor,
            )
        )
    return candidates


def _to_entries(
    ranked: list[PrioritizedCell],
    candidates: list[PrioritizationCandidate],
    grid_by_id: dict[str, GridCell],
) -> list[BrigadeRankEntry]:
    """Enriquece ranking com coordenadas e justificativa."""
    candidate_by_id = {item.cell_id: item for item in candidates}
    entries: list[BrigadeRankEntry] = []
    for item in ranked:
        candidate = candidate_by_id[item.cell_id]
        grid_cell = grid_by_id.get(item.cell_id)
        if grid_cell is not None:
            lat, lon = grid_cell.lat_center, grid_cell.lon_center
        else:
            lat, lon = parse_cell_center(item.cell_id)
        entries.append(
            BrigadeRankEntry(
                rank=item.rank,
                cell_id=item.cell_id,
                lat_center=lat,
                lon_center=lon,
                priority_score=item.priority_score,
                risk_score=item.risk_score,
                band=item.band,
                fires_1d=candidate.fires_1d,
                fires_7d=candidate.fires_7d,
                neighbor_fires_7d=candidate.neighbor_fires_7d,
                justification=build_justification(candidate),
            )
        )
    return entries


def _export_ranking(
    processed_dir: Path,
    reference_date: date,
    top_n: int,
    entries: list[BrigadeRankEntry],
) -> tuple[Path, Path]:
    """Grava JSON e CSV do ranking em data/processed/."""
    processed_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "reference_date": reference_date.isoformat(),
        "top_n": top_n,
        "entries": [_entry_to_dict(entry) for entry in entries],
    }
    json_path = processed_dir / BRIGADE_RANKING_JSON
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    csv_path = processed_dir / BRIGADE_RANKING_CSV
    fieldnames = list(_entry_to_dict(entries[0]).keys()) if entries else [
        "rank",
        "cell_id",
        "lat_center",
        "lon_center",
        "priority_score",
        "risk_score",
        "band",
        "fires_1d",
        "fires_7d",
        "neighbor_fires_7d",
        "justification",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for entry in entries:
            writer.writerow(_entry_to_dict(entry))

    return json_path, csv_path


def _entry_to_dict(entry: BrigadeRankEntry) -> dict[str, object]:
    """Serializa entrada do ranking para export."""
    return {
        "rank": entry.rank,
        "cell_id": entry.cell_id,
        "lat_center": entry.lat_center,
        "lon_center": entry.lon_center,
        "priority_score": entry.priority_score,
        "risk_score": entry.risk_score,
        "band": entry.band,
        "fires_1d": entry.fires_1d,
        "fires_7d": entry.fires_7d,
        "neighbor_fires_7d": entry.neighbor_fires_7d,
        "justification": entry.justification,
    }


def main() -> None:
    """Entrypoint: python -m src.application.rank_brigades"""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    report = rank_brigades()
    print(
        f"Ranking: ref={report.reference_date} top_n={report.top_n} "
        f"candidates={report.total_candidates} json={report.json_path} "
        f"csv={report.csv_path}"
    )


if __name__ == "__main__":
    main()
