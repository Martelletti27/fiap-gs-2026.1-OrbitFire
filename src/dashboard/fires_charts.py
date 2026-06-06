"""Graficos de comportamento de focos no Tocantins."""

from __future__ import annotations

from typing import Any

import altair as alt
import pandas as pd
import streamlit as st

MONTH_LABELS = {
    "01": "Jan",
    "02": "Fev",
    "03": "Mar",
    "04": "Abr",
    "05": "Mai",
    "06": "Jun",
    "07": "Jul",
    "08": "Ago",
    "09": "Set",
    "10": "Out",
    "11": "Nov",
    "12": "Dez",
}

_CHART_THEME = {
    "view": {"stroke": "transparent"},
    "axis": {"labelFontSize": 11, "titleFontSize": 12},
}

DEFAULT_TOP_CELLS = 15


def render_fires_charts(summary: dict[str, Any]) -> None:
    """Exibe graficos de sazonalidade e ranking historico por quadrante."""
    st.subheader("Comportamento de focos no Tocantins")
    st.caption(
        "Historico NASA FIRMS no estado — sazonalidade e quadrantes com mais "
        "deteccoes ajudam a contextualizar o risco preditivo."
    )

    if summary.get("total_in_region", 0) == 0:
        st.info("Sem focos registrados no Tocantins para gerar graficos.")
        return

    _render_monthly_chart(summary)
    _render_cell_ranking_chart(summary)


def _render_monthly_chart(summary: dict[str, Any]) -> None:
    """Sazonalidade ordenada cronologicamente na linha do tempo."""
    rows = sort_monthly_rows(summary.get("monthly_counts", []))
    if not rows:
        st.warning("Sem dados mensais de focos.")
        return

    df = pd.DataFrame(rows)
    df["rotulo"] = df["month"].map(_month_label)
    order = df["rotulo"].tolist()

    chart = (
        alt.Chart(df)
        .mark_bar(color="#e67e22", cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
        .encode(
            x=alt.X(
                "rotulo:N",
                sort=order,
                title="Mes (ordem cronologica)",
                axis=alt.Axis(labelAngle=0),
            ),
            y=alt.Y("count:Q", title="Focos"),
            tooltip=[
                alt.Tooltip("rotulo:N", title="Mes"),
                alt.Tooltip("count:Q", title="Focos", format=","),
            ],
        )
        .properties(height=260, title="Sazonalidade — focos por mes")
        .configure(**_CHART_THEME)
    )
    st.altair_chart(chart, use_container_width=True)


def _render_cell_ranking_chart(summary: dict[str, Any]) -> None:
    """Top quadrantes da grade com mais focos no historico."""
    if "cell_ranking" not in summary:
        st.warning(
            "Ranking de quadrantes indisponivel na API. "
            "Reinicie o servidor: uvicorn src.api.main:app --port 8001"
        )
        return

    rows = summary.get("cell_ranking", [])
    if not rows:
        st.warning("Sem ranking de quadrantes disponivel para o Tocantins.")
        return

    df = pd.DataFrame(rows)
    df["quadrante"] = df.apply(
        lambda row: f"#{int(row['rank'])} {row['cell_id']}",
        axis=1,
    )
    order = df.sort_values("rank")["quadrante"].tolist()

    chart = (
        alt.Chart(df)
        .mark_bar(color="#c0392b", cornerRadiusEnd=3)
        .encode(
            y=alt.Y(
                "quadrante:N",
                sort=order,
                title="Quadrante (rank)",
            ),
            x=alt.X("count:Q", title="Focos historicos"),
            tooltip=[
                alt.Tooltip("rank:Q", title="Rank"),
                alt.Tooltip("cell_id:N", title="Celula"),
                alt.Tooltip("lat:Q", title="Lat", format=".2f"),
                alt.Tooltip("lon:Q", title="Lon", format=".2f"),
                alt.Tooltip("count:Q", title="Focos", format=","),
            ],
        )
        .properties(
            height=max(220, len(df) * 22),
            title=f"Ranking historico de focos por quadrante (Top {len(df)})",
        )
        .configure(**_CHART_THEME)
    )
    st.altair_chart(chart, use_container_width=True)


def sort_monthly_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Ordena meses YYYY-MM na linha do tempo."""
    return sorted(rows, key=lambda row: str(row["month"]))


def _month_label(month_key: str) -> str:
    """Converte YYYY-MM em rotulo legivel (ex.: Jun/24)."""
    year, month = month_key.split("-")
    label = MONTH_LABELS.get(month, month)
    return f"{label}/{year[2:]}"
