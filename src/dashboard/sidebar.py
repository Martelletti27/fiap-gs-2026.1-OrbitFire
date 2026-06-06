"""Filtros globais do painel."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import streamlit as st

from src.config import REGION, UFS
from src.dashboard.formatters import format_date_short

BAND_OPTIONS = ("Todos", "baixo", "medio", "alto", "critico")
TOP_N_OPTIONS = (10, 20, 50)
DEFAULT_UF = UFS[0]


@dataclass(frozen=True)
class DashboardFilters:
    """Filtros selecionados na sidebar."""

    reference_date: date | None
    band: str | None
    uf: str
    top_n: int
    show_fires: bool


def render_sidebar(default_reference: date | None) -> DashboardFilters:
    """Renderiza controles laterais e retorna filtros ativos."""
    st.sidebar.header("Filtros")
    reference_date = _reference_date_display(default_reference)
    band = _band_filter()
    uf = _uf_display()
    top_n = st.sidebar.selectbox(
        "Top-N prioridade",
        options=TOP_N_OPTIONS,
        index=0,
        help="Quantidade de celulas no ranking de brigadas.",
    )
    show_fires = st.sidebar.checkbox(
        "Exibir focos ativos no mapa",
        value=True,
        help="Sobrepoe deteccoes FIRMS recentes ao mapa de risco preditivo.",
    )
    return DashboardFilters(
        reference_date=reference_date,
        band=band,
        uf=uf,
        top_n=int(top_n),
        show_fires=show_fires,
    )


def _reference_date_display(default_reference: date | None) -> date | None:
    """Exibe data de referencia fixa quando ha apenas um dia disponivel."""
    if default_reference is None:
        st.sidebar.info("Aguardando data de referencia da API.")
        return None
    st.sidebar.text_input(
        "Data de referencia",
        value=format_date_short(default_reference),
        disabled=True,
        help="Unica data com scores inferidos no banco.",
    )
    return default_reference


def _band_filter() -> str | None:
    """Filtro de nivel de risco."""
    choice = st.sidebar.selectbox(
        "Nivel de risco",
        options=BAND_OPTIONS,
        help="Filtra celulas exibidas no mapa.",
    )
    return None if choice == "Todos" else choice


def _uf_display() -> str:
    """UF fixa do escopo do projeto."""
    st.sidebar.text_input(
        "UF",
        value=f"{DEFAULT_UF} — {REGION}",
        disabled=True,
        help="OrbitFire cobre apenas o Tocantins.",
    )
    return DEFAULT_UF
