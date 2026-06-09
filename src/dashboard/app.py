"""Painel Streamlit do OrbitFire — consome apenas a API REST.

Execucao:
    $env:PYTHONPATH = "."
    streamlit run src/dashboard/app.py
"""

from __future__ import annotations

from datetime import date

import streamlit as st

# set_page_config deve ser o primeiro comando Streamlit do modulo.
# Posicionado antes dos demais imports para garantir que nenhuma
# importacao dispare comandos st.* antes desta configuracao.
st.set_page_config(
    page_title="OrbitFire",
    layout="wide",
    initial_sidebar_state="expanded",
)

from src.config import load_settings
from src.dashboard.api_client import ApiClientError, OrbitFireApiClient
from src.dashboard.fires_charts import render_fires_charts
from src.dashboard.kpis import render_kpis
from src.dashboard.map_view import filter_risk_map_to_to, render_risk_map
from src.dashboard.ranking_view import render_ranking
from src.dashboard.sidebar import render_sidebar

# Tagline exibida abaixo do titulo — explica o projeto sem abrir o README.
_TAGLINE = (
    "Cruza deteccoes satelitais NASA FIRMS com clima local para indicar "
    "onde o risco de incendio amanha e maior no Tocantins e priorizar brigadas."
)


def main() -> None:
    """Entrypoint principal do painel OrbitFire."""
    st.title("OrbitFire")
    st.caption(_TAGLINE)

    settings = load_settings()

    # BUG 1 CORRIGIDO: from_settings() nao existe no OrbitFireApiClient.
    # O construtor aceita apenas base_url (str), conforme test_dashboard_api_client.py.
    client = OrbitFireApiClient(settings.api_base_url)

    # Health check: exibe instrucao acionavel e para se a API nao responder.
    try:
        health = client.health()
    except ApiClientError:
        st.error(
            "API indisponivel. Suba a API antes de abrir o dashboard:\n\n"
            "uvicorn src.api.main:app --host 127.0.0.1 --port 8000"
        )
        st.stop()

    # Sidebar: filtros e status offline/online.
    default_ref = _parse_reference_date(health.get("reference_date"))
    filters = render_sidebar(default_ref)

    # Exibe modo operacional na sidebar apos carregar o health.
    mode_label = "Modo Offline" if health.get("offline_mode") else "Modo Online"
    st.sidebar.caption(f"{mode_label} | {settings.api_base_url}")

    # ── Busca dados da API (cada secao trata erro independentemente) ──────────

    risk_map: dict = {}
    try:
        # BUG 2 CORRIGIDO: client.risk_map() retorna dict completo.
        # filter_risk_map_to_to() recebe o dict e devolve versao filtrada
        # com total_cells (~2285) e band_counts corretos para o poligono TO.
        risk_map = filter_risk_map_to_to(
            client.risk_map(
                reference_date=filters.reference_date,
                band=filters.band,
                uf=filters.uf,
            )
        )
    except ApiClientError as exc:
        st.warning(f"Mapa de risco indisponivel: {exc}")

    fires_payload: dict = {"fires": []}
    try:
        # BUG 3 CORRIGIDO: fires_active() nao aceita parametro hours=24.
        fires_payload = client.fires_active()
    except ApiClientError:
        fires_payload = {"fires": []}

    fires_summary: dict = {}
    try:
        fires_summary = client.fires_summary(days=30, top_cells=15)
    except ApiClientError:
        pass

    ranking: dict = {}
    try:
        ranking = client.risk_ranking(
            reference_date=filters.reference_date or default_ref,
            top_n=filters.top_n,
        )
    except ApiClientError as exc:
        st.warning(f"Ranking indisponivel: {exc}")

    # BUG 4 CORRIGIDO: fires_payload.get("total", 0) retornava sempre 0
    # porque o endpoint retorna {"fires": [...]} sem chave "total".
    active_fires_24h = len(fires_payload.get("fires", []))

    # ── KPIs ─────────────────────────────────────────────────────────────────
    render_kpis(health, risk_map, active_fires_24h=active_fires_24h)
    st.divider()

    # ── Mapa de risco preditivo ───────────────────────────────────────────────
    # Passa o dict completo de focos; render_risk_map extrai fires.get("fires").
    fires_para_mapa = fires_payload if filters.show_fires else None
    render_risk_map(risk_map, fires_para_mapa, show_fires=filters.show_fires)
    st.divider()

    # ── Graficos de comportamento historico de focos ──────────────────────────
    if fires_summary:
        render_fires_charts(fires_summary)
    else:
        st.info(
            "Dados historicos de focos indisponiveis. "
            "Verifique se o endpoint /fires/summary esta implementado na API."
        )
    st.divider()

    # ── Ranking de brigadas ───────────────────────────────────────────────────
    render_ranking(ranking)


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
