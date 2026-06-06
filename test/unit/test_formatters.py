"""Testes de formatacao do dashboard."""

from datetime import date

from src.dashboard.formatters import format_date_short


def test_format_date_short_two_digit_year() -> None:
    """Data deve aparecer como dd/mm/aa."""
    assert format_date_short(date(2024, 9, 30)) == "30/09/24"


def test_format_date_short_none() -> None:
    """Valor ausente retorna traco."""
    assert format_date_short(None) == "—"
