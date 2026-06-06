"""Tabela de prioridade de brigadas e export CSV."""

from __future__ import annotations

import csv
import io
from typing import Any

import streamlit as st

RANKING_COLUMNS = {
    "rank": "Posicao",
    "cell_id": "Celula",
    "risk_score": "Risco",
    "priority_score": "Prioridade",
    "band": "Faixa",
    "justificativa": "Justificativa",
}


def render_ranking(ranking: dict[str, Any]) -> None:
    """Exibe Top-N e botao de download CSV."""
    st.subheader("Prioridade de brigadas")
    entries = ranking.get("entries", [])
    if not entries:
        st.info("Nenhuma celula no ranking para os filtros atuais.")
        return

    table_rows = [
        {
            "rank": item["rank"],
            "cell_id": item["cell_id"],
            "risk_score": item["risk_score"],
            "priority_score": item["priority_score"],
            "band": item["band"],
            "justificativa": item["justificativa"],
        }
        for item in entries
    ]
    st.dataframe(
        table_rows,
        column_config={
            "rank": st.column_config.NumberColumn(RANKING_COLUMNS["rank"]),
            "cell_id": st.column_config.TextColumn(RANKING_COLUMNS["cell_id"]),
            "risk_score": st.column_config.NumberColumn(
                RANKING_COLUMNS["risk_score"],
                format="%.1f",
            ),
            "priority_score": st.column_config.NumberColumn(
                RANKING_COLUMNS["priority_score"],
                format="%.1f",
            ),
            "band": st.column_config.TextColumn(RANKING_COLUMNS["band"]),
            "justificativa": st.column_config.TextColumn(
                RANKING_COLUMNS["justificativa"],
                width="large",
            ),
        },
        hide_index=True,
        use_container_width=True,
    )

    csv_text = _entries_to_csv(table_rows)
    st.download_button(
        "Exportar CSV",
        data=csv_text,
        file_name="orbitfire_ranking.csv",
        mime="text/csv",
        help="Baixa o ranking exibido com as colunas da API.",
    )


def _entries_to_csv(rows: list[dict[str, Any]]) -> str:
    """Serializa linhas do ranking para CSV."""
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(RANKING_COLUMNS.keys()))
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()
