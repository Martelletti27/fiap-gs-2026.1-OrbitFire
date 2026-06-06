"""Testes dos graficos de focos."""

from src.dashboard.fires_charts import sort_monthly_rows


def test_sort_monthly_rows_chronological() -> None:
    """Meses devem seguir ordem YYYY-MM na linha do tempo."""
    rows = [
        {"month": "2024-09", "count": 100},
        {"month": "2024-06", "count": 10},
        {"month": "2024-08", "count": 50},
    ]
    sorted_rows = sort_monthly_rows(rows)
    assert [row["month"] for row in sorted_rows] == [
        "2024-06",
        "2024-08",
        "2024-09",
    ]
