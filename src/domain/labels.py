"""Regra pura do label: incendio na celula no dia seguinte (D+1)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from src.domain.features import FirePoint

PROGRESS_EVERY_CELLS = 100


@dataclass(frozen=True)
class CellDayLabel:
    """Label binario para treino: fogo amanha na mesma celula."""

    cell_id: str
    day: date
    fire_tomorrow: int


def labelable_reference_days(
    fires: list[FirePoint],
    days: list[date],
) -> list[date]:
    """Mantem apenas dias cujo D+1 existe na janela observada de focos."""
    if not fires:
        return []
    max_fire_day = max(point.day for point in fires)
    return sorted(
        day for day in set(days) if day + timedelta(days=1) <= max_fire_day
    )


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
    ordered_days = labelable_reference_days(fires, sorted(set(days)))
    fire_days_by_cell = _group_fire_days(fires)
    total_cells = len(cell_ids)

    rows: list[CellDayLabel] = []
    for index, cell_id in enumerate(cell_ids, start=1):
        cell_fire_days = fire_days_by_cell.get(cell_id, set())
        for day in ordered_days:
            tomorrow = day + timedelta(days=1)
            rows.append(
                CellDayLabel(
                    cell_id=cell_id,
                    day=day,
                    fire_tomorrow=1 if tomorrow in cell_fire_days else 0,
                )
            )
        if index % PROGRESS_EVERY_CELLS == 0 or index == total_cells:
            _print_labels_progress(index, total_cells)
    return rows


def _group_fire_days(fires: list[FirePoint]) -> dict[str, set[date]]:
    """Indexa dias com foco por celula."""
    result: dict[str, set[date]] = {}
    for point in fires:
        result.setdefault(point.cell_id, set()).add(point.day)
    return result


def _print_labels_progress(done: int, total: int) -> None:
    """Exibe progresso da geracao de labels por celula."""
    percent = 100.0 * done / total if total else 100.0
    print(f"Progresso labels: {done}/{total} ({percent:.1f}%)", flush=True)
