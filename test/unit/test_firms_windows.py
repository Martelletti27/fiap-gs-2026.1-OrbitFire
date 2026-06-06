"""Testes das janelas de datas FIRMS SP."""

from datetime import date

from src.domain.firms_windows import iter_firms_date_windows


def test_iter_firms_date_windows_covers_jun_sep_2024() -> None:
    """Periodo jun-set/2024 deve gerar janelas contiguas de ate 5 dias (SP)."""
    windows = iter_firms_date_windows(
        date(2024, 6, 1),
        date(2024, 9, 30),
        max_chunk_days=5,
    )

    assert len(windows) == 25
    assert windows[0] == (date(2024, 6, 1), 5)
    assert windows[-1] == (date(2024, 9, 29), 2)
    assert sum(day_range for _, day_range in windows) == 122
