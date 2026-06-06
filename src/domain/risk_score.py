"""Conversao de probabilidade do modelo em score 0-100 e faixas de risco."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

RISK_BANDS: tuple[str, ...] = ("baixo", "medio", "alto", "critico")
THRESHOLDS_FILENAME = "thresholds.json"
DEFAULT_PERCENTILES: tuple[float, float, float] = (50.0, 75.0, 90.0)
MIN_THRESHOLD_GAP = 1.0


@dataclass(frozen=True)
class RiskThresholds:
    """Limites minimos de score para subir de faixa (medio < alto < critico)."""

    medio: float
    alto: float
    critico: float

    def __post_init__(self) -> None:
        if not (0.0 <= self.medio < self.alto < self.critico <= 100.0):
            raise ValueError(
                "Limites invalidos: esperado 0 <= medio < alto < critico <= 100"
            )


@dataclass(frozen=True)
class RiskAssessment:
    """Resultado da conversao probabilidade -> score operacional."""

    probability: float
    score: float
    band: str


DEFAULT_THRESHOLDS = RiskThresholds(medio=25.0, alto=50.0, critico=75.0)


def probability_to_score(probability: float) -> float:
    """Escala probabilidade 0-1 para score 0-100."""
    clamped = max(0.0, min(1.0, float(probability)))
    return round(clamped * 100.0, 2)


def classify_band(score: float, thresholds: RiskThresholds) -> str:
    """Classifica faixa a partir do score e limites calibrados."""
    if score >= thresholds.critico:
        return "critico"
    if score >= thresholds.alto:
        return "alto"
    if score >= thresholds.medio:
        return "medio"
    return "baixo"


def assess_risk(probability: float, thresholds: RiskThresholds) -> RiskAssessment:
    """Converte probabilidade bruta em score e faixa operacional."""
    score = probability_to_score(probability)
    band = classify_band(score, thresholds)
    return RiskAssessment(probability=probability, score=score, band=band)


def derive_thresholds_from_probabilities(
    probabilities: list[float],
    *,
    percentiles: tuple[float, float, float] = DEFAULT_PERCENTILES,
) -> RiskThresholds:
    """Calibra limites por percentis do conjunto de referencia (ex.: treino)."""
    if not probabilities:
        return DEFAULT_THRESHOLDS

    scores = [probability_to_score(value) for value in probabilities]
    raw = (
        _percentile(scores, percentiles[0]),
        _percentile(scores, percentiles[1]),
        _percentile(scores, percentiles[2]),
    )
    return _normalize_threshold_triplet(raw)


def thresholds_to_dict(
    thresholds: RiskThresholds,
    *,
    method: str = "score_percentile",
    percentiles: tuple[float, float, float] = DEFAULT_PERCENTILES,
    reference_rows: int | None = None,
) -> dict[str, object]:
    """Serializa limites para JSON em data/models/thresholds.json."""
    payload: dict[str, object] = {
        "version": 1,
        "bands": list(RISK_BANDS),
        "method": method,
        "percentiles": {
            "medio": percentiles[0],
            "alto": percentiles[1],
            "critico": percentiles[2],
        },
        "score_limits": {
            "medio": thresholds.medio,
            "alto": thresholds.alto,
            "critico": thresholds.critico,
        },
        "calibrated_at": datetime.now(timezone.utc).isoformat(),
    }
    if reference_rows is not None:
        payload["reference_rows"] = reference_rows
    return payload


def thresholds_from_dict(payload: dict[str, object]) -> RiskThresholds:
    """Carrega limites a partir de thresholds.json."""
    limits = payload.get("score_limits")
    if not isinstance(limits, dict):
        raise ValueError("thresholds.json sem score_limits")

    try:
        return RiskThresholds(
            medio=float(limits["medio"]),
            alto=float(limits["alto"]),
            critico=float(limits["critico"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("score_limits incompleto ou invalido") from exc


def load_thresholds(path: Path) -> RiskThresholds:
    """Le limites calibrados do disco."""
    if not path.is_file():
        raise FileNotFoundError(f"Arquivo de thresholds nao encontrado: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"thresholds.json invalido: {path}")
    return thresholds_from_dict(payload)


def save_thresholds(
    path: Path,
    thresholds: RiskThresholds,
    *,
    method: str = "score_percentile",
    percentiles: tuple[float, float, float] = DEFAULT_PERCENTILES,
    reference_rows: int | None = None,
) -> Path:
    """Grava limites calibrados para uso em inferencia e dashboard."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = thresholds_to_dict(
        thresholds,
        method=method,
        percentiles=percentiles,
        reference_rows=reference_rows,
    )
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def _percentile(values: list[float], percentile: float) -> float:
    """Percentil linear sem dependencias externas."""
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]

    rank = (len(ordered) - 1) * (percentile / 100.0)
    low = int(rank)
    high = min(low + 1, len(ordered) - 1)
    weight = rank - low
    return ordered[low] * (1.0 - weight) + ordered[high] * weight


def _normalize_threshold_triplet(raw: tuple[float, float, float]) -> RiskThresholds:
    """Garante ordem estrita e gap minimo entre faixas."""
    values = [round(value, 2) for value in raw]
    for index in range(1, len(values)):
        values[index] = max(values[index], values[index - 1] + MIN_THRESHOLD_GAP)

    if values[2] > 100.0:
        values[2] = 100.0
        values[1] = min(values[1], 100.0 - MIN_THRESHOLD_GAP)
        values[0] = min(values[0], values[1] - MIN_THRESHOLD_GAP)

    try:
        return RiskThresholds(medio=values[0], alto=values[1], critico=values[2])
    except ValueError:
        return DEFAULT_THRESHOLDS
