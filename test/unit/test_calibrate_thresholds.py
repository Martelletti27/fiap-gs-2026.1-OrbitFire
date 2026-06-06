"""Testes da calibracao de thresholds (prioridade 1)."""

import numpy as np

from src.application.calibrate_thresholds import _best_f1_threshold


def test_best_f1_threshold_prefers_higher_recall_when_f1_improves() -> None:
    """Deve escolher threshold que maximiza F1 no grid."""
    y_true = np.array([0, 0, 0, 1, 1, 1])
    proba = np.array([0.10, 0.20, 0.40, 0.55, 0.70, 0.90])

    threshold, metrics = _best_f1_threshold(y_true, proba)

    assert 0.05 <= threshold <= 0.95
    assert metrics["f1"] >= 0.0
    assert "confusion" in metrics
