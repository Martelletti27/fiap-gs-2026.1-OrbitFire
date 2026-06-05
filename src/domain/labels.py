"""Regra pura do label: incendio na celula no dia seguinte (D+1)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from src.domain.features import FirePoint


@dataclass(frozen=True)
class CellDayLabel:
    """Label binario para treino: fogo amanha na mesma celula."""

    cell_id: str
    day: date
    fire_tomorrow: int


def fire_tomorrow_label(
    cell_id: str,
    day: date,
    fires: list[FirePoint],
) -> int:
    """Retorna 1 se houver foco FIRMS na celula em D+1; senao 0."""
    tomorrow = day + timedelta(days=1)
    for point in fires:
        if point.cell_id == cell_id and point.day == tomorrow:
            return 1
    return 0


def build_labels_table(
    cell_ids: list[str],
    days: list[date],
    fires: list[FirePoint],
) -> list[CellDayLabel]:
    """Gera labels para o produto celulas x dias de referencia."""
    ordered_days = sorted(set(days))
    rows: list[CellDayLabel] = []
    for cell_id in cell_ids:
        for day in ordered_days:
            rows.append(
                CellDayLabel(
                    cell_id=cell_id,
                    day=day,
                    fire_tomorrow=fire_tomorrow_label(cell_id, day, fires),
                )
            )
    return rows
