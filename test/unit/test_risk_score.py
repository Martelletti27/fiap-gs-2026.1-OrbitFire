"""Testes de score 0-100 e faixas de risco (S3.E2)."""

import json
from pathlib import Path

import pytest

from src.domain.risk_score import (
    DEFAULT_THRESHOLDS,
    RiskAssessment,
    RiskThresholds,
    assess_risk,
    classify_band,
    derive_thresholds_from_probabilities,
    load_thresholds,
    probability_to_score,
    save_thresholds,
    thresholds_from_dict,
)


def test_probability_to_score_scales_and_clamps() -> None:
    """Probabilidade vira score 0-100 com clamp."""
    assert probability_to_score(0.0) == 0.0
    assert probability_to_score(1.0) == 100.0
    assert probability_to_score(0.456) == 45.6
    assert probability_to_score(-0.2) == 0.0
    assert probability_to_score(1.5) == 100.0


def test_classify_band_boundaries() -> None:
    """Faixas respeitam limites inclusivos no topo."""
    thresholds = RiskThresholds(medio=25.0, alto=50.0, critico=75.0)

    assert classify_band(0.0, thresholds) == "baixo"
    assert classify_band(24.99, thresholds) == "baixo"
    assert classify_band(25.0, thresholds) == "medio"
    assert classify_band(49.99, thresholds) == "medio"
    assert classify_band(50.0, thresholds) == "alto"
    assert classify_band(74.99, thresholds) == "alto"
    assert classify_band(75.0, thresholds) == "critico"
    assert classify_band(100.0, thresholds) == "critico"


def test_assess_risk_end_to_end() -> None:
    """Pipeline probabilidade -> score -> faixa."""
    result = assess_risk(0.82, DEFAULT_THRESHOLDS)
    assert result == RiskAssessment(probability=0.82, score=82.0, band="critico")


def test_derive_thresholds_from_probabilities_uses_percentiles() -> None:
    """Calibracao por percentis separa faixas mesmo com classe rara."""
    probabilities = [0.01, 0.02, 0.03, 0.05, 0.08, 0.12, 0.20, 0.35, 0.60, 0.90]
    thresholds = derive_thresholds_from_probabilities(probabilities)

    assert thresholds.medio < thresholds.alto < thresholds.critico
    assert assess_risk(0.01, thresholds).band == "baixo"
    assert assess_risk(0.90, thresholds).band == "critico"


def test_derive_thresholds_empty_returns_default() -> None:
    """Sem referencia, usa quartis fixos padrao."""
    assert derive_thresholds_from_probabilities([]) == DEFAULT_THRESHOLDS


def test_thresholds_roundtrip_json(tmp_path: Path) -> None:
    """Salvar e carregar thresholds.json preserva limites."""
    path = tmp_path / "thresholds.json"
    custom = RiskThresholds(medio=10.0, alto=30.0, critico=60.0)

    save_thresholds(path, custom, method="fixed_quartiles", reference_rows=100)
    loaded = load_thresholds(path)

    assert loaded == custom
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["score_limits"]["medio"] == 10.0
    assert payload["reference_rows"] == 100


def test_thresholds_from_dict_rejects_invalid_payload() -> None:
    """JSON sem score_limits deve falhar."""
    with pytest.raises(ValueError, match="score_limits"):
        thresholds_from_dict({"version": 1})


def test_risk_thresholds_rejects_non_monotonic_limits() -> None:
    """Limites fora de ordem nao sao aceitos."""
    with pytest.raises(ValueError, match="Limites invalidos"):
        RiskThresholds(medio=80.0, alto=50.0, critico=90.0)
