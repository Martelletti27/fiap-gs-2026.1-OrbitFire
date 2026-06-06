"""KPIs do topo do painel."""

from __future__ import annotations

from typing import Any

import streamlit as st

from src.dashboard.formatters import format_date_short


def render_kpis(
    health: dict[str, Any],
    risk_map: dict[str, Any],
    *,
    active_fires_24h: int,
) -> None:
    """Exibe metricas principais alinhadas ao contrato de dados."""
    band_counts = risk_map.get("band_counts", {})
    high_risk = band_counts.get("alto", 0) + band_counts.get("critico", 0)
    ref_raw = risk_map.get("reference_date", health.get("reference_date"))
    ref_text = format_date_short(ref_raw)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric(
        "Celulas monitoradas",
        risk_map.get("total_cells", health.get("grid_cells", 0)),
    )
    col2.metric("Alto + critico", high_risk)
    col3.metric("Focos ativos (24h)", active_fires_24h)
    col4.metric("Data de referencia", ref_text)
