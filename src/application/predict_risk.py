"""Caso de uso: inferencia batch de risco por celula (fogo amanha)."""

from __future__ import annotations

import logging
import pickle
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd

from src.application.db_loaders import (
    load_fire_points,
    load_weather_points,
    require_non_empty_grid,
)
from src.config import Settings, load_settings
from src.domain.features import (
    CellDayFeatures,
    FirePoint,
    WeatherPoint,
    build_features_table,
)
from src.domain.risk_score import THRESHOLDS_FILENAME, assess_risk, load_thresholds
from src.infrastructure.db.repository import repository_session
from src.infrastructure.ml.train import FEATURE_COLUMNS, MODEL_FILENAME

logger = logging.getLogger(__name__)
PROGRESS_EVERY_CELLS = 500


@dataclass(frozen=True)
class PredictRiskReport:
    """Resumo da inferencia batch persistida em risk_scores."""

    reference_date: date
    cell_count: int
    scores_written: int
    band_counts: dict[str, int]
    model_path: Path
    thresholds_path: Path


def predict_risk(
    settings: Settings | None = None,
    reference_date: date | None = None,
) -> PredictRiskReport:
    """Gera score e faixa por celula para a data de referencia e grava no SQLite."""
    cfg = settings or load_settings()
    model_path = cfg.models_dir / MODEL_FILENAME
    thresholds_path = cfg.models_dir / THRESHOLDS_FILENAME
    _require_model_artifacts(model_path, thresholds_path)

    print("Carregando modelo e thresholds...", flush=True)
    with model_path.open("rb") as handle:
        model = pickle.load(handle)
    thresholds = load_thresholds(thresholds_path)

    with repository_session(cfg.db_path) as repository:
        print("Carregando grade e dados operacionais...", flush=True)
        grid_cells = require_non_empty_grid(repository, "predict_risk")
        cell_ids = [cell.cell_id for cell in grid_cells]
        fires = load_fire_points(repository, cfg.bbox, cfg.grid_deg)
        weather = load_weather_points(repository)
        ref_day = reference_date or _resolve_reference_date(weather, fires)
        print(
            f"Inferencia: {len(cell_ids)} celulas | referencia={ref_day.isoformat()}",
            flush=True,
        )

        feature_rows = _build_inference_features(
            cell_ids,
            ref_day,
            fires,
            weather,
            cfg.grid_deg,
        )
        probabilities = _predict_probabilities(model, feature_rows)
        band_counter: Counter[str] = Counter()

        for index, (cell_id, features) in enumerate(feature_rows, start=1):
            probability = float(probabilities[index - 1])
            assessment = assess_risk(probability, thresholds)
            repository.upsert_risk_score(
                cell_id=cell_id,
                reference_date=ref_day,
                score=assessment.score,
                band=assessment.band,
                probability=assessment.probability,
            )
            band_counter[assessment.band] += 1
            if index % PROGRESS_EVERY_CELLS == 0 or index == len(feature_rows):
                _print_predict_progress(index, len(feature_rows))

    report = PredictRiskReport(
        reference_date=ref_day,
        cell_count=len(cell_ids),
        scores_written=len(cell_ids),
        band_counts=dict(band_counter),
        model_path=model_path,
        thresholds_path=thresholds_path,
    )
    logger.info(
        "Inferencia: ref=%s cells=%s bands=%s",
        ref_day,
        len(cell_ids),
        report.band_counts,
    )
    return report


def _require_model_artifacts(model_path: Path, thresholds_path: Path) -> None:
    """Garante artefatos de treino antes da inferencia."""
    if not model_path.is_file():
        raise FileNotFoundError(
            f"Modelo nao encontrado: {model_path}. "
            "Execute python -m src.infrastructure.ml.train antes"
        )
    if not thresholds_path.is_file():
        raise FileNotFoundError(
            f"Thresholds nao encontrados: {thresholds_path}. "
            "Execute python -m src.application.calibrate_thresholds antes"
        )


def _resolve_reference_date(
    weather: list[WeatherPoint],
    fires: list[FirePoint],
) -> date:
    """Usa o dia mais recente com clima; fallback para focos FIRMS."""
    if weather:
        return max(point.day for point in weather)
    if fires:
        return max(point.day for point in fires)
    raise ValueError(
        "Sem dados de clima ou focos FIRMS para definir data de referencia"
    )


def _build_inference_features(
    cell_ids: list[str],
    reference_date: date,
    fires: list[FirePoint],
    weather: list[WeatherPoint],
    grid_deg: float,
) -> list[tuple[str, CellDayFeatures]]:
    """Monta features por celula na data de referencia (lote indexado)."""
    print("Calculando features de inferencia...", flush=True)
    feature_rows = build_features_table(
        cell_ids,
        [reference_date],
        fires,
        weather,
        grid_deg=grid_deg,
    )
    return [(row.cell_id, row) for row in feature_rows]


def _predict_probabilities(model, feature_rows: list[tuple[str, CellDayFeatures]]) -> list[float]:
    """Aplica modelo LightGBM ao lote de features."""
    frame = pd.DataFrame(
        [_features_to_record(features) for _, features in feature_rows]
    )
    missing = set(FEATURE_COLUMNS) - set(frame.columns)
    if missing:
        raise ValueError(f"Features de inferencia incompletas: {sorted(missing)}")
    x_frame = frame.loc[:, FEATURE_COLUMNS].apply(pd.to_numeric, errors="coerce")
    return model.predict_proba(x_frame)[:, 1].tolist()


def _features_to_record(features: CellDayFeatures) -> dict[str, object]:
    """Converte CellDayFeatures para linha compativel com o treino."""
    return {
        "fires_1d": features.fires_1d,
        "fires_7d": features.fires_7d,
        "fires_30d": features.fires_30d,
        "days_without_rain": features.days_without_rain,
        "temp_mean_7d": features.temp_mean_7d,
        "precip_sum_7d": features.precip_sum_7d,
        "wind_mean_7d": features.wind_mean_7d,
        "neighbor_fires_7d": features.neighbor_fires_7d,
        "season_month": features.season_month,
    }


def _print_predict_progress(done: int, total: int) -> None:
    """Exibe progresso da inferencia por celula."""
    percent = 100.0 * done / total if total else 100.0
    print(f"Progresso inferencia: {done}/{total} ({percent:.1f}%)", flush=True)


def main() -> None:
    """Entrypoint: python -m src.application.predict_risk"""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    report = predict_risk()
    print(
        f"Inferencia: ref={report.reference_date} cells={report.cell_count} "
        f"written={report.scores_written} bands={report.band_counts}"
    )


if __name__ == "__main__":
    main()
