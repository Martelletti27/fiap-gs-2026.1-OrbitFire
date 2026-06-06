"""Testes da regra de label fogo amanha (S2.E2)."""

from datetime import date

from src.domain.features import FirePoint
from src.domain.labels import (
    build_labels_table,
    fire_tomorrow_label,
    labelable_reference_days,
)


def test_fire_tomorrow_label_positive() -> None:
    """Label 1 quando ha foco na celula no dia seguinte."""
    ref = date(2026, 6, 1)
    fires = [FirePoint("GO_-16.00_-49.10", date(2026, 6, 2))]
    assert fire_tomorrow_label("GO_-16.00_-49.10", ref, fires) == 1


def test_fire_tomorrow_label_negative_same_day() -> None:
    """Foco no mesmo dia nao conta como amanha."""
    ref = date(2026, 6, 2)
    fires = [FirePoint("GO_-16.00_-49.10", date(2026, 6, 2))]
    assert fire_tomorrow_label("GO_-16.00_-49.10", ref, fires) == 0


def test_fire_tomorrow_label_negative_other_cell() -> None:
    """Foco em outra celula nao altera o label."""
    ref = date(2026, 6, 1)
    fires = [FirePoint("MT_-12.50_-55.10", date(2026, 6, 2))]
    assert fire_tomorrow_label("GO_-16.00_-49.10", ref, fires) == 0


def test_labelable_reference_days_excludes_last_day() -> None:
    """Ultimo dia sem D+1 observavel nao entra nas labels."""
    days = [date(2026, 6, 1), date(2026, 6, 2), date(2026, 6, 3)]
    fires = [
        FirePoint("DF_-15.80_-47.90", date(2026, 6, 1)),
        FirePoint("DF_-15.80_-47.90", date(2026, 6, 3)),
    ]
    assert labelable_reference_days(fires, days) == [date(2026, 6, 1), date(2026, 6, 2)]


def test_build_labels_table_shape() -> None:
    """Tabela de labels cobre celulas x dias labelaveis."""
    days = [date(2026, 6, 1), date(2026, 6, 2)]
    fires = [FirePoint("DF_-15.80_-47.90", date(2026, 6, 2))]
    rows = build_labels_table(["DF_-15.80_-47.90", "GO_-16.00_-49.10"], days, fires)
    assert len(rows) == 2
    positive = [row for row in rows if row.fire_tomorrow == 1]
    assert len(positive) == 1
    assert positive[0].cell_id == "DF_-15.80_-47.90"
    assert positive[0].day == date(2026, 6, 1)
