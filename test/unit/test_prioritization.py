"""Testes de priorizacao de celulas para brigadas (S4.E1)."""

import pytest

from src.domain.prioritization import (
    PrioritizationCandidate,
    build_justification,
    compute_priority_score,
    rank_priorities,
)


def test_compute_priority_score_uses_risk_as_base() -> None:
    """Score composto parte do risk_score sem focos recentes."""
    low = PrioritizationCandidate("TO_A", risk_score=20.0, band="baixo")
    high = PrioritizationCandidate("TO_B", risk_score=80.0, band="baixo")
    assert compute_priority_score(high) > compute_priority_score(low)


def test_compute_priority_score_boosts_recent_fires() -> None:
    """Focos 1d elevam prioridade acima do risco isolado."""
    base = PrioritizationCandidate("TO_A", risk_score=50.0, band="medio")
    with_fires = PrioritizationCandidate(
        "TO_B",
        risk_score=50.0,
        band="medio",
        fires_1d=2,
        fires_7d=3,
        neighbor_fires_7d=1,
    )
    assert compute_priority_score(with_fires) > compute_priority_score(base)
    assert compute_priority_score(with_fires) == pytest.approx(62.0)


def test_compute_priority_score_caps_at_100() -> None:
    """Prioridade nao ultrapassa 100 mesmo com muitos focos."""
    hot = PrioritizationCandidate(
        "TO_HOT",
        risk_score=95.0,
        band="critico",
        fires_1d=10,
        fires_7d=20,
        neighbor_fires_7d=15,
    )
    assert compute_priority_score(hot) == 100.0


def test_rank_priorities_orders_by_priority_score() -> None:
    """Ranking respeita score composto e atribui posicoes 1..N."""
    candidates = [
        PrioritizationCandidate("TO_LOW", risk_score=10.0, band="baixo"),
        PrioritizationCandidate(
            "TO_HIGH",
            risk_score=70.0,
            band="alto",
            fires_1d=1,
        ),
        PrioritizationCandidate("TO_MID", risk_score=40.0, band="medio"),
    ]
    ranked = rank_priorities(candidates)

    assert [item.cell_id for item in ranked] == ["TO_HIGH", "TO_MID", "TO_LOW"]
    assert ranked[0].rank == 1
    assert ranked[1].rank == 2
    assert ranked[2].rank == 3


def test_rank_priorities_top_n_limits_results() -> None:
    """Top-N retorna apenas as primeiras posicoes."""
    candidates = [
        PrioritizationCandidate(f"TO_{index}", risk_score=float(index), band="baixo")
        for index in range(5)
    ]
    ranked = rank_priorities(candidates, top_n=2)
    assert len(ranked) == 2
    assert ranked[0].cell_id == "TO_4"
    assert ranked[1].cell_id == "TO_3"


def test_rank_priorities_tiebreaks_by_band_then_risk() -> None:
    """Empate de prioridade desempata por faixa e risk_score."""
    candidates = [
        PrioritizationCandidate("TO_A", risk_score=60.0, band="medio"),
        PrioritizationCandidate("TO_B", risk_score=60.0, band="critico"),
    ]
    ranked = rank_priorities(candidates)
    assert ranked[0].cell_id == "TO_B"
    assert ranked[1].cell_id == "TO_A"


def test_build_justification_lists_operational_reasons() -> None:
    """Justificativa deve citar faixa e focos recentes."""
    candidate = PrioritizationCandidate(
        "TO_-10.05_-47.90",
        risk_score=72.0,
        band="alto",
        fires_1d=2,
        neighbor_fires_7d=1,
    )
    text = build_justification(candidate)
    assert "faixa alto" in text
    assert "24h" in text
    assert "vizinhas" in text


def test_rank_priorities_empty_and_zero_top_n() -> None:
    """Lista vazia ou top_n invalido retorna sem erro."""
    assert rank_priorities([]) == []
    candidate = PrioritizationCandidate("TO_A", risk_score=10.0, band="baixo")
    assert rank_priorities([candidate], top_n=0) == []
