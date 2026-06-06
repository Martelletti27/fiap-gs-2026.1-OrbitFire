"""Formatacao de datas e textos do painel."""

from __future__ import annotations

from datetime import date, datetime


def format_date_short(value: date | datetime | str | None) -> str:
    """Formata data como dd/mm/aa para exibicao no painel."""
    if value is None:
        return "—"
    if isinstance(value, datetime):
        parsed = value.date()
    elif isinstance(value, date):
        parsed = value
    else:
        parsed = date.fromisoformat(str(value)[:10])
    return parsed.strftime("%d/%m/%y")
