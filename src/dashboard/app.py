"""Painel Streamlit do OrbitFire — consome apenas a API REST."""

from __future__ import annotations

from datetime import date

import streamlit as st

from src.config import load_settings
from src.dashboard.api_client import ApiClientError, OrbitFireApiClient
from src.dashboard.fires_charts import render_fires_charts
from src.dashboard.kpis import render_kpis
from src.dashboard.map_view import filter_risk_map_to_to, render_risk_map
from src.dashboard.ranking_view import render_ranking

PROJECT_TAGLINE = (
    "Cruza deteccoes satelitais NASA FIRMS com clima local para indicar "
    "onde o risco de incendio amanha e maior no Tocantins e priorizar brigadas."
)
from src.dashboard.sidebar import render_sidebar


def main() -> None:
    """Entrypoint: streamlit run src/dashboard/app.py"""
    st.set_page_config(
        page_title="OrbitFire",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.title("OrbitFire")
    st.caption("Risco preditivo de incendio para o Tocantins (TO)")

    settings = load_settings()
    client = OrbitFireApiClient.from_settings(settings)

    try:
        health = client.health()
    except ApiClientError as exc:
        st.error(str(exc))
        st.stop()

    default_ref = _parse_reference_date(health.get("reference_date"))
    filters = render_sidebar(default_ref)

    try:
        risk_map = filter_risk_map_to_to(
            client.risk_map(
                reference_date=filters.reference_date,
                band=filters.band,
                uf=filters.uf,
            )
        )
        ranking = client.risk_ranking(
            reference_date=filters.reference_date or default_ref,
            top_n=filters.top_n,
        )
        fires_payload = client.fires_active(hours=24)
        fires_summary = client.fires_summary(days=30, top_cells=15)
        fires = fires_payload if filters.show_fires else None
    except ApiClientError as exc:
        st.error(str(exc))
        st.stop()

    mode_label = "Modo Offline" if health.get("offline_mode") else "Modo Online"
    st.sidebar.caption(f"API: {settings.api_base_url} | {mode_label}")

    render_kpis(health, risk_map, active_fires_24h=fires_payload.get("total", 0))
    st.divider()
    render_risk_map(risk_map, fires, show_fires=filters.show_fires)
    st.divider()
    render_fires_charts(fires_summary)
    st.divider()
    render_ranking(ranking)


def _parse_reference_date(value: str | date | None) -> date | None:
    """Converte data ISO retornada pela API."""
    if value is None:
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


if __name__ == "__main__":
    main()
