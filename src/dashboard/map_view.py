"""Mapa de risco preditivo com Folium."""

from __future__ import annotations

from collections import Counter
from typing import Any

import folium
import streamlit as st
from folium.plugins import HeatMap
from streamlit_folium import st_folium

from src.config import GRID_DEG
from src.domain.to_boundary import TO_BOUNDARY, boundary_bounds, is_in_tocantins

HEAT_RADIUS = 7
HEAT_BLUR = 10
HEAT_MIN_OPACITY = 0.15

BAND_COLORS = {
    "alto": "#e67e22",
    "critico": "#c0392b",
}

RISK_GRADIENT = {
    0.0: "#27ae60",
    0.4: "#f1c40f",
    0.65: "#e67e22",
    1.0: "#c0392b",
}

HIGHLIGHT_BANDS = frozenset({"alto", "critico"})

MAP_LEGEND_HTML = """
<div style="
    position: fixed;
    bottom: 14px;
    right: 14px;
    z-index: 9999;
    background: rgba(255, 255, 255, 0.94);
    color: #111;
    padding: 6px 9px;
    border: 1px solid #333;
    border-radius: 4px;
    box-shadow: 0 1px 6px rgba(0, 0, 0, 0.25);
    font-size: 10px;
    font-family: Arial, sans-serif;
    line-height: 1.35;
    max-width: 185px;
    min-width: 165px;
">
  <div style="font-weight: 700; margin-bottom: 3px;">Risco</div>
  <div style="
      height: 7px;
      border-radius: 2px;
      border: 1px solid #444;
      background: linear-gradient(to right, #27ae60, #f1c40f, #e67e22, #c0392b);
      margin-bottom: 2px;
  "></div>
  <div style="display:flex; justify-content:space-between;">
    <span>Baixo</span><span>Critico</span>
  </div>
  <div style="margin-top:3px; color:#444;">
    &#9679; alto/critico
  </div>
</div>
"""


def filter_risk_map_to_to(risk_map: dict[str, Any]) -> dict[str, Any]:
    """Recalcula payload do mapa mantendo apenas celulas dentro do TO."""
    cells = _cells_inside_to(risk_map.get("cells", []))
    return {
        **risk_map,
        "cells": cells,
        "total_cells": len(cells),
        "band_counts": dict(Counter(cell["band"] for cell in cells)),
    }


def render_risk_map(
    risk_map: dict[str, Any],
    fires: dict[str, Any] | None,
    *,
    show_fires: bool,
) -> None:
    """Renderiza mapa de calor com hotspots e legenda dentro do mapa."""
    st.subheader("Mapa de risco preditivo")
    cells = risk_map.get("cells", [])
    if not cells:
        st.info("Nenhum score para o Tocantins nos filtros selecionados.")
        return

    high_count = sum(1 for c in cells if c["band"] in HIGHLIGHT_BANDS)
    st.caption(
        f"{len(cells)} celulas no TO | {high_count} em alto/critico. "
        "Pontos laranja/vermelho marcam as areas de maior risco."
    )

    folium_map = _build_folium_map(cells, fires, show_fires=show_fires)
    st_folium(folium_map, width=None, height=520, returned_objects=[])


def _build_folium_map(
    cells: list[dict[str, Any]],
    fires: dict[str, Any] | None,
    *,
    show_fires: bool,
) -> folium.Map:
    """Monta mapa Folium com heatmap, marcadores e legenda interna."""
    lat_min, lat_max, lon_min, lon_max = boundary_bounds()
    center_lat = (lat_min + lat_max) / 2
    center_lon = (lon_min + lon_max) / 2
    folium_map = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=7,
        tiles="CartoDB positron",
        max_bounds=[[lat_min - 0.5, lon_min - 0.5], [lat_max + 0.5, lon_max + 0.5]],
    )
    folium_map.fit_bounds([[lat_min, lon_min], [lat_max, lon_max]])

    folium.Polygon(
        locations=[(lat, lon) for lat, lon in TO_BOUNDARY],
        color="#2c3e50",
        weight=2,
        fill=False,
    ).add_to(folium_map)

    heat_data = _build_heat_data(cells)
    if heat_data:
        HeatMap(
            heat_data,
            name="Risco preditivo",
            radius=HEAT_RADIUS,
            blur=HEAT_BLUR,
            min_opacity=HEAT_MIN_OPACITY,
            max_zoom=18,
            gradient=RISK_GRADIENT,
        ).add_to(folium_map)

    _add_high_risk_markers(folium_map, cells)

    if show_fires and fires:
        _add_fire_markers(folium_map, fires)

    folium_map.get_root().html.add_child(folium.Element(MAP_LEGEND_HTML))
    return folium_map


def _add_high_risk_markers(
    folium_map: folium.Map,
    cells: list[dict[str, Any]],
) -> None:
    """Marcadores pequenos com borda e sombra na cor da faixa."""
    for cell in cells:
        if cell["band"] not in HIGHLIGHT_BANDS:
            continue
        color = BAND_COLORS[cell["band"]]
        size = 5 if cell["band"] == "critico" else 4
        folium.Marker(
            location=[cell["lat"], cell["lon"]],
            icon=_glow_marker_icon(color, size_px=size),
            popup=(
                f"{cell['cell_id']}<br>"
                f"Score: {cell['score']:.1f}<br>"
                f"Faixa: {cell['band']}"
            ),
        ).add_to(folium_map)


def _add_fire_markers(folium_map: folium.Map, fires: dict[str, Any]) -> None:
    """Marca focos FIRMS recentes dentro do TO."""
    fire_color = "#ff0000"
    for fire in fires.get("fires", []):
        if not is_in_tocantins(fire["lat"], fire["lon"]):
            continue
        folium.Marker(
            location=[fire["lat"], fire["lon"]],
            icon=_glow_marker_icon(fire_color, size_px=4),
            popup=f"Foco {fire['source']}",
        ).add_to(folium_map)


def _glow_marker_icon(color: str, *, size_px: int) -> folium.DivIcon:
    """Icone circular com borda na mesma cor e sombra suave."""
    shadow = _shadow_rgba(color)
    return folium.DivIcon(
        html=f"""
        <div style="
            width:{size_px}px;
            height:{size_px}px;
            background:{color};
            border:1px solid {color};
            border-radius:50%;
            box-shadow: 0 1px 2px rgba(0,0,0,0.3), 0 0 5px {shadow};
        "></div>
        """,
        icon_size=(size_px, size_px),
        icon_anchor=(size_px // 2, size_px // 2),
    )


def _shadow_rgba(hex_color: str, alpha: float = 0.55) -> str:
    """Converte hex em rgba para sombra colorida."""
    raw = hex_color.lstrip("#")
    red = int(raw[0:2], 16)
    green = int(raw[2:4], 16)
    blue = int(raw[4:6], 16)
    return f"rgba({red},{green},{blue},{alpha})"


def _build_heat_data(cells: list[dict[str, Any]]) -> list[list[float]]:
    """Peso relativo ao recorte exibido — realca picos e atenua baixo."""
    if not cells:
        return []

    scores = [cell["score"] for cell in cells]
    score_min = min(scores)
    score_max = max(scores)
    span = max(score_max - score_min, 1.0)

    heat_data: list[list[float]] = []
    for cell in cells:
        if cell["band"] == "baixo":
            weight = 0.04
        else:
            normalized = (cell["score"] - score_min) / span
            weight = 0.12 + 0.88 * (normalized**1.35)
        heat_data.append([cell["lat"], cell["lon"], weight])
    return heat_data


def _cells_inside_to(cells: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Mantem apenas celulas dentro do contorno do TO."""
    return [
        cell
        for cell in cells
        if cell.get("uf") == "TO" and is_in_tocantins(cell["lat"], cell["lon"])
    ]
