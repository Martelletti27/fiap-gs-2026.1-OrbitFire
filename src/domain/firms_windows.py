"""Janelas de datas para ingestao historica FIRMS SP."""

from __future__ import annotations

from datetime import date, timedelta


def iter_firms_date_windows(
    period_start: date,
    period_end: date,
    *,
    max_chunk_days: int = 10,
) -> list[tuple[date, int]]:
    """Divide periodo em janelas (data_inicio, day_range) para API area/csv.

    A NASA retorna registros de DATE ate DATE + DAY_RANGE - 1.
    """
    if period_start > period_end:
        raise ValueError("period_start deve ser anterior ou igual a period_end")

    chunk = max(1, min(max_chunk_days, 10))
    windows: list[tuple[date, int]] = []
    cursor = period_start

    while cursor <= period_end:
        window_end = min(cursor + timedelta(days=chunk - 1), period_end)
        day_range = (window_end - cursor).days + 1
        windows.append((cursor, day_range))
        cursor = window_end + timedelta(days=1)

    return windows
