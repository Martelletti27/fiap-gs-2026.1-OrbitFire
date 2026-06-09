"""Painel Streamlit do OrbitFire — consome apenas a API REST.

Execucao:
    $env:PYTHONPATH = "."
    streamlit run src/dashboard/app.py
"""

from __future__ import annotations

# set_page_config DEVE ser o primeiro comando Streamlit do modulo.
# Se vier depois de qualquer outro st.*, lanca StreamlitAPIException.
import streamlit as st

st.set_page_config(
    page_title="OrbitFire",
    layout="wide",
    initial_sidebar_state="expanded",
)

from datetime import date

from src.config import load_settings
from src.dashboard.api_client import ApiClientError, OrbitFireApiClient
from src.dashboard.fires_charts import render_fires_charts
from src.dashboard.kpis import render_kpis
from src.dashboard.map_view import filter_risk_map_to_to, render_risk_map
from src.dashboard.ranking_view import render_ranking
from src.dashboard.sidebar import render_sidebar

# Tagline exibida abaixo do titulo — explica o projeto sem abrir o README
_TAGLINE = (
    "Cruza deteccoes satelitais NASA FIRMS com clima local para indicar "
    "onde o risco de incendio amanha e maior no Tocantins — e priorizar brigadas."
)


# Cache de 5 minutos para nao sobrecarregar a API a cada re-render do Streamlit.
# A chave de cache e a URL da API, nao o objeto cliente (que nao e hashavel).
@st.cache_data(ttl=300, show_spinner=False)
def _cached_risk_map(base_url: str, band: str | None, reference_date: str | None) -> dict:
    """Busca mapa de risco e mantém cache por 5 minutos."""
    client = OrbitFireApiClient(base_url)
    return client.risk_map(band=band, reference_date=reference_date)


@st.cache_data(ttl=300, show_spinner=False)
def _cached_fires_summary(base_url: str) -> dict:
    """Busca resumo historico de focos e mantém cache por 5 minutos."""
    client = OrbitFireApiClient(base_url)
    return client.fires_summary(days=30, top_cells=15)


def main() -> None:
    """Entrypoint principal do painel OrbitFire."""
    st.title("OrbitFire")
    st.caption(_TAGLINE)

    settings = load_settings()

    # BUG CORRIGIDO: o construtor recebe base_url (str), nao o objeto settings.
    # OrbitFireApiClient.from_settings() nao existe — causava AttributeError.
    client = OrbitFireApiClient(settings.api_base_url)

    # Health check: se a API nao responder, exibe instrucao acionavel e para.
    try:
        health = client.health()
    except ApiClientError:
        st.error(
            "API indisponivel. Suba a API antes de abrir o dashboard:\n\n"
            "uvicorn src.api.main:app --host 127.0.0.1 --port 8000"
        )
        st.stop()

    # Sidebar: filtros globais e status offline/online
    filters = render_sidebar(client)

    # ── Secao de KPIs ────────────────────────────────────────────────────────
    # BUG CORRIGIDO: risk_map() retorna dict {"cells": [...], ...},
    # nao uma lista direta. filter_risk_map_to_to() espera lista.
    cells: list[dict] = []
    fires_active: list[dict] = []

    try:
        risk_payload = _cached_risk_map(
            settings.api_base_url,
            band=filters.get("band") if filters.get("band") != "Todos" else None,
            reference_date=filters.get("reference_date"),
        )
        # Extrai a lista de celulas do payload e filtra para o poligono TO
        raw_cells = risk_payload.get("cells", [])
        cells = filter_risk_map_to_to(raw_cells)
    except ApiClientError as exc:
        st.warning(f"Mapa de risco indisponivel: {exc}")

    try:
        # BUG CORRIGIDO: fires_active() nao aceita parametro hours=24.
        # A assinatura real e client.fires_active() sem argumentos.
        fires_payload = client.fires_active()
        # Extrai lista de eventos do payload (estrutura: {"fires": [...]} ou lista direta)
        fires_active = (
            fires_payload if isinstance(fires_payload, list)
            else fires_payload.get("fires", [])
        )
    except ApiClientError:
        fires_active = []

    # KPIs usam o mesmo recorte do mapa (celulas dentro do TO)
    render_kpis(
        cells=cells,
        fires_active=fires_active,
        reference_date=filters.get("reference_date"),
    )

    st.divider()

    # ── Mapa de risco preditivo ───────────────────────────────────────────────
    st.subheader("Mapa de risco preditivo — Tocantins")
    if cells:
        render_risk_map(
            cells=cells,
            fire_events=fires_active if filters.get("show_fires") else [],
            show_fires=filters.get("show_fires", True),
        )
    else:
        st.info(
            "Nenhum dado de risco disponivel para o periodo selecionado. "
            "Execute predict_risk para gerar scores."
        )

    st.divider()

    # ── Graficos de comportamento historico de focos ──────────────────────────
    # BUG CORRIGIDO: era chamado sem tratar ApiClientError,
    # causando crash silencioso se /fires/summary nao existir.
    try:
        summary = _cached_fires_summary(settings.api_base_url)
        render_fires_charts(summary)
    except ApiClientError:
        st.warning(
            "Dados historicos de focos indisponiveis. "
            "Verifique se o endpoint /fires/summary esta implementado na API."
        )

    st.divider()

    # ── Ranking de brigadas ───────────────────────────────────────────────────
    try:
        # BUG CORRIGIDO: parametro era reference_date=filters.reference_date
        # mas filters e um dict, nao um objeto com atributos.
        ranking = client.risk_ranking(
            top_n=filters.get("top_n", 10),
            reference_date=filters.get("reference_date"),
        )
        render_ranking(ranking.get("entries", []), top_n=filters.get("top_n", 10))
    except ApiClientError as exc:
        st.warning(f"Ranking de brigadas indisponivel: {exc}")


def _parse_reference_date(value: str | date | None) -> date | None:
    """Converte data ISO retornada pela API para objeto date."""
    if value is None:
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


if __name__ == "__main__":
    main()
