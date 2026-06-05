"""Exportacao de artefatos em data/processed/."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

GRID_CELLS_PARQUET = "grid_cells.parquet"
FEATURES_PARQUET = "features_cell_day.parquet"
LABELS_PARQUET = "labels_cell_day.parquet"
DATASET_PARQUET = "dataset_cell_day.parquet"
DATASET_SPLIT_JSON = "dataset_split.json"


def write_parquet(
    processed_dir: Path,
    filename: str,
    rows: list[dict[str, object]] | pd.DataFrame,
) -> Path:
    """Grava parquet em data/processed/ criando o diretorio se necessario."""
    processed_dir.mkdir(parents=True, exist_ok=True)
    path = processed_dir / filename
    frame = rows if isinstance(rows, pd.DataFrame) else pd.DataFrame(rows)
    frame.to_parquet(path, index=False)
    return path
