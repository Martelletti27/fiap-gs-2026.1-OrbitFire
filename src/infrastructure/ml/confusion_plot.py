"""Gera imagem da matriz de confusao e metricas do treino."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

CONFUSION_MATRIX_FILENAME = "confusion_matrix.png"
TITLE_Y = 0.935
KPI_FONT_SIZE = 12
KPI_LINE_STEP = 0.058
KPI_TOP_GAP_LINES = 2
KPI_X_ALIGN = 0.98


def save_confusion_matrix_image(
    models_dir: Path,
    confusion: dict[str, int],
    metrics: dict[str, object],
    *,
    filename: str = CONFUSION_MATRIX_FILENAME,
) -> Path:
    """Salva heatmap da matriz de confusao com acuracia e erro."""
    models_dir.mkdir(parents=True, exist_ok=True)
    path = models_dir / filename

    matrix = _confusion_to_matrix(confusion)
    fig = plt.figure(figsize=(11, 6))
    grid = fig.add_gridspec(
        1,
        2,
        width_ratios=[0.95, 4.2],
        wspace=0.025,
        left=0.06,
        right=0.96,
        top=0.88,
        bottom=0.14,
    )
    kpi_ax = fig.add_subplot(grid[0, 0])
    kpi_ax.axis("off")
    ax = fig.add_subplot(grid[0, 1])

    fig.text(
        0.58,
        TITLE_Y,
        "Matriz de confusao — teste",
        ha="center",
        va="center",
        fontsize=13,
        fontweight="bold",
    )
    _draw_heatmap(ax, matrix)
    _draw_metrics_text(kpi_ax, metrics, confusion)

    fig.savefig(path, dpi=120, bbox_inches="tight", pad_inches=0.12)
    plt.close(fig)
    return path


def _confusion_to_matrix(confusion: dict[str, int]) -> np.ndarray:
    """Monta matriz 2x2 a partir de tp/tn/fp/fn."""
    tn = int(confusion.get("tn", 0))
    fp = int(confusion.get("fp", 0))
    fn = int(confusion.get("fn", 0))
    tp = int(confusion.get("tp", 0))
    return np.array([[tn, fp], [fn, tp]], dtype=int)


def _draw_heatmap(ax: plt.Axes, matrix: np.ndarray) -> None:
    """Desenha matriz de confusao com anotacoes."""
    labels_pred = ["Sem fogo (pred)", "Com fogo (pred)"]
    labels_true = ["Sem fogo (real)", "Com fogo (real)"]

    im = ax.imshow(matrix, cmap="Blues")
    ax.set_xticks([0, 1], labels=labels_pred)
    ax.set_yticks([0, 1], labels=labels_true)
    ax.tick_params(axis="x", pad=8)
    ax.set_xlabel("Previsao do modelo", labelpad=14)
    ax.set_ylabel("Valor real", labelpad=8)
    for row in range(2):
        for col in range(2):
            value = int(matrix[row, col])
            color = "white" if value > matrix.max() / 2 else "black"
            ax.text(col, row, str(value), ha="center", va="center", color=color, fontsize=14)

    plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)


def _draw_metrics_text(
    kpi_ax: plt.Axes,
    metrics: dict[str, object],
    confusion: dict[str, int],
) -> None:
    """Exibe KPIs a esquerda da matriz, com folga antes da primeira linha."""
    display = _metrics_for_display(metrics, confusion)
    lines = [
        f"Acuracia: {display['accuracy'] * 100:.2f}%",
        f"Erro: {display['error_rate'] * 100:.2f}%",
        f"Precisao: {display['precision']:.4f}",
        f"Recall: {display['recall']:.4f}",
        f"F1: {display['f1']:.4f}",
        f"AUC-ROC: {display['auc_text']}",
        f"Amostras teste: {display['test_rows']}",
    ]
    panel = kpi_ax.get_position()
    first_y = TITLE_Y - KPI_TOP_GAP_LINES * KPI_LINE_STEP
    for index, line in enumerate(lines):
        fig_y = first_y - index * KPI_LINE_STEP
        ax_y = (fig_y - panel.y0) / panel.height
        kpi_ax.text(
            KPI_X_ALIGN,
            ax_y,
            line,
            ha="right",
            va="center",
            fontsize=KPI_FONT_SIZE,
            transform=kpi_ax.transAxes,
        )


def _metrics_for_display(
    metrics: dict[str, object],
    confusion: dict[str, int],
) -> dict[str, object]:
    """Normaliza metricas vindas do treino ou da calibracao."""
    accuracy = float(metrics.get("accuracy", metrics.get("optimal_accuracy", 0.0)))
    precision = float(metrics.get("precision", metrics.get("optimal_precision", 0.0)))
    recall = float(metrics.get("recall", metrics.get("optimal_recall", 0.0)))
    f1 = float(metrics.get("f1", metrics.get("optimal_f1", 0.0)))
    roc_auc = metrics.get("roc_auc")
    auc_text = "N/A" if roc_auc is None else f"{float(roc_auc):.4f}"

    test_rows = int(metrics.get("test_rows", 0))
    if test_rows == 0:
        test_rows = sum(int(confusion.get(key, 0)) for key in ("tp", "tn", "fp", "fn"))

    return {
        "accuracy": accuracy,
        "error_rate": 1.0 - accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "auc_text": auc_text,
        "test_rows": test_rows,
    }
