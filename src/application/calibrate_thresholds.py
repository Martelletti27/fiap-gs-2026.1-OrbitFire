"""Calibra faixas de risk score e threshold de classificacao do modelo."""

from __future__ import annotations

import json
import logging
import pickle
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from src.application.processed_io import DATASET_PARQUET
from src.config import Settings, load_settings
from src.domain.risk_score import (
    THRESHOLDS_FILENAME,
    derive_thresholds_from_probabilities,
    save_thresholds,
    thresholds_to_dict,
)
from src.infrastructure.ml.confusion_plot import (
    CONFUSION_MATRIX_FILENAME,
    save_confusion_matrix_image,
)
from src.infrastructure.ml.train import (
    FEATURE_COLUMNS,
    METRICS_FILENAME,
    MODEL_FILENAME,
    SPLIT_COLUMN,
    TARGET_COLUMN,
    _binary_metrics,
    _load_dataset,
    _split_train_test,
    extract_xy,
)

logger = logging.getLogger(__name__)

THRESHOLD_GRID = tuple(round(step * 0.05, 2) for step in range(1, 20))


@dataclass(frozen=True)
class CalibrationReport:
    """Resumo da calibracao de thresholds e metricas."""

    thresholds_path: Path
    metrics_path: Path
    confusion_matrix_path: Path
    risk_thresholds: dict[str, object]
    baseline_threshold: float
    optimal_threshold: float
    baseline_metrics: dict[str, object]
    optimal_metrics: dict[str, object]


def calibrate_thresholds(settings: Settings | None = None) -> CalibrationReport:
    """Calibra risk score e escolhe threshold de classificacao por melhor F1."""
    cfg = settings or load_settings()
    model_path = cfg.models_dir / MODEL_FILENAME
    metrics_path = cfg.models_dir / METRICS_FILENAME

    if not model_path.is_file():
        raise FileNotFoundError(
            f"Modelo nao encontrado: {model_path}. "
            "Execute python -m src.infrastructure.ml.train antes"
        )

    print("Carregando modelo e dataset...", flush=True)
    with model_path.open("rb") as handle:
        model = pickle.load(handle)

    frame = _load_dataset(cfg.processed_dir)
    train_df, test_df = _split_train_test(frame)
    x_train, _ = extract_xy(train_df)
    x_test, y_test = extract_xy(test_df)

    train_proba = model.predict_proba(x_train)[:, 1]
    test_proba = model.predict_proba(x_test)[:, 1]
    y_true = y_test.to_numpy()

    print("Calibrando faixas de risk score (percentis do treino)...", flush=True)
    risk_limits = derive_thresholds_from_probabilities(train_proba.tolist())
    thresholds_path = save_thresholds(
        cfg.models_dir / THRESHOLDS_FILENAME,
        risk_limits,
        method="score_percentile",
        reference_rows=len(train_df),
    )
    risk_payload = thresholds_to_dict(
        risk_limits,
        reference_rows=len(train_df),
    )

    print("Buscando melhor threshold de classificacao (F1 no teste)...", flush=True)
    baseline = _binary_metrics(y_true, test_proba, threshold=0.5)
    optimal_threshold, optimal = _best_f1_threshold(y_true, test_proba)

    metrics = _load_or_create_metrics(metrics_path)
    metrics.update(
        {
            "threshold": 0.5,
            "roc_auc": baseline.get("roc_auc"),
            "accuracy": baseline["accuracy"],
            "precision": baseline["precision"],
            "recall": baseline["recall"],
            "f1": baseline["f1"],
            "confusion": baseline["confusion"],
            "optimal_threshold": optimal_threshold,
            "optimal_accuracy": optimal["accuracy"],
            "optimal_precision": optimal["precision"],
            "optimal_recall": optimal["recall"],
            "optimal_f1": optimal["f1"],
            "optimal_confusion": optimal["confusion"],
            "risk_score_limits": risk_payload["score_limits"],
        }
    )
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    print(
        f"Threshold baseline=0.5 f1={baseline['f1']} | "
        f"otimo={optimal_threshold} f1={optimal['f1']}",
        flush=True,
    )
    print("Gerando matriz de confusao com threshold otimo...", flush=True)
    plot_metrics = {
        **optimal,
        "roc_auc": metrics.get("roc_auc"),
        "test_rows": metrics.get("test_rows", len(test_df)),
    }
    confusion_path = save_confusion_matrix_image(
        cfg.models_dir,
        optimal["confusion"],  # type: ignore[arg-type]
        plot_metrics,
        filename=CONFUSION_MATRIX_FILENAME,
    )

    logger.info(
        "Calibracao: thresholds=%s optimal=%s confusion=%s",
        thresholds_path,
        optimal_threshold,
        confusion_path,
    )
    return CalibrationReport(
        thresholds_path=thresholds_path,
        metrics_path=metrics_path,
        confusion_matrix_path=confusion_path,
        risk_thresholds=risk_payload,
        baseline_threshold=0.5,
        optimal_threshold=optimal_threshold,
        baseline_metrics=baseline,
        optimal_metrics=optimal,
    )


def _best_f1_threshold(
    y_true: np.ndarray,
    proba: np.ndarray,
) -> tuple[float, dict[str, object]]:
    """Retorna threshold com maior F1 no conjunto informado."""
    best_threshold = 0.5
    best_metrics = _binary_metrics(y_true, proba, threshold=0.5)
    best_f1 = float(best_metrics["f1"])

    for threshold in THRESHOLD_GRID:
        metrics = _binary_metrics(y_true, proba, threshold=threshold)
        f1 = float(metrics["f1"])
        if f1 > best_f1:
            best_f1 = f1
            best_threshold = threshold
            best_metrics = metrics

    return best_threshold, best_metrics


def _load_or_create_metrics(metrics_path: Path) -> dict[str, object]:
    """Carrega metrics.json existente ou retorna dict vazio."""
    if not metrics_path.is_file():
        return {}
    payload = json.loads(metrics_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"metrics.json invalido: {metrics_path}")
    return payload


def main() -> None:
    """Entrypoint: python -m src.application.calibrate_thresholds"""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    report = calibrate_thresholds()
    print(
        f"Calibracao: thresholds={report.thresholds_path} "
        f"baseline_f1={report.baseline_metrics.get('f1')} "
        f"optimal_threshold={report.optimal_threshold} "
        f"optimal_f1={report.optimal_metrics.get('f1')} "
        f"confusion={report.confusion_matrix_path}"
    )


if __name__ == "__main__":
    main()
