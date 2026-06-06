"""Treino do classificador LightGBM para fogo amanha."""

from __future__ import annotations

import json
import logging
import pickle
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd

from src.application.processed_io import DATASET_PARQUET
from src.config import Settings, ensure_data_dirs, load_settings
from src.domain.features import FEATURE_COLUMN_NAMES
from src.infrastructure.ml.confusion_plot import (
    CONFUSION_MATRIX_FILENAME,
    save_confusion_matrix_image,
)

logger = logging.getLogger(__name__)

FEATURE_COLUMNS = FEATURE_COLUMN_NAMES
TARGET_COLUMN = "fire_tomorrow"
SPLIT_COLUMN = "split"
MODEL_FILENAME = "lgbm_orbitfire.pkl"
METRICS_FILENAME = "metrics.json"

DEFAULT_LGBM_PARAMS: dict[str, object] = {
    "objective": "binary",
    "metric": "auc",
    "learning_rate": 0.05,
    "num_leaves": 31,
    "min_child_samples": 20,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "random_state": 42,
    "n_estimators": 200,
    "verbose": -1,
}

# Grid enxuto para tuning no holdout temporal (S3 tuning).
CANDIDATE_PARAM_SETS: tuple[dict[str, object], ...] = (
    {},
    {
        "num_leaves": 63,
        "min_child_samples": 30,
        "max_depth": 8,
        "subsample": 0.85,
        "colsample_bytree": 0.85,
    },
    {
        "learning_rate": 0.03,
        "num_leaves": 31,
        "min_child_samples": 50,
        "max_depth": 6,
        "subsample": 0.9,
        "colsample_bytree": 0.9,
    },
    {
        "learning_rate": 0.04,
        "num_leaves": 47,
        "min_child_samples": 40,
        "max_depth": 7,
        "subsample": 0.85,
        "colsample_bytree": 0.8,
    },
    {
        "num_leaves": 15,
        "min_child_samples": 100,
        "max_depth": 5,
        "subsample": 0.75,
        "colsample_bytree": 0.75,
    },
    {
        "learning_rate": 0.06,
        "num_leaves": 31,
        "min_child_samples": 25,
        "max_depth": -1,
        "subsample": 0.8,
        "colsample_bytree": 0.9,
    },
)


@dataclass(frozen=True)
class TrainReport:
    """Resumo do treino e avaliacao no conjunto de teste."""

    model_path: Path
    metrics_path: Path
    confusion_matrix_path: Path
    train_rows: int
    test_rows: int
    metrics: dict[str, object]


def train_model(settings: Settings | None = None) -> TrainReport:
    """Treina LightGBM com dataset_cell_day.parquet e salva modelo e metricas."""
    cfg = settings or load_settings()
    ensure_data_dirs(cfg)

    print("Carregando dataset...", flush=True)
    frame = _load_dataset(cfg.processed_dir)
    train_df, test_df = _split_train_test(frame)
    print(
        f"Treino: {len(train_df)} linhas | Teste: {len(test_df)} linhas",
        flush=True,
    )
    print("Buscando hiperparametros LightGBM...", flush=True)
    best_params, tuning_auc = tune_lgbm_params(train_df, test_df)
    print("Ajustando LightGBM com params selecionados...", flush=True)
    model = _fit_classifier(train_df, test_df, params=best_params)
    print("Avaliando modelo...", flush=True)
    metrics = _evaluate_model(model, train_df, test_df)
    metrics["lgbm_params"] = _resolved_lgbm_params(best_params, train_df)
    metrics["tuning_candidates"] = len(CANDIDATE_PARAM_SETS)
    metrics["tuning_best_auc"] = tuning_auc

    print("Salvando modelo e metricas...", flush=True)
    model_path = _save_model(cfg.models_dir, model)
    metrics_path = _save_metrics(cfg.models_dir, metrics)
    confusion_path = save_confusion_matrix_image(
        cfg.models_dir,
        metrics["confusion"],  # type: ignore[arg-type]
        metrics,
        filename=CONFUSION_MATRIX_FILENAME,
    )

    logger.info(
        "Treino: train=%s test=%s auc=%s model=%s confusion=%s",
        len(train_df),
        len(test_df),
        metrics.get("roc_auc"),
        model_path,
        confusion_path,
    )
    return TrainReport(
        model_path=model_path,
        metrics_path=metrics_path,
        confusion_matrix_path=confusion_path,
        train_rows=len(train_df),
        test_rows=len(test_df),
        metrics=metrics,
    )


def _load_dataset(processed_dir: Path) -> pd.DataFrame:
    """Carrega dataset consolidado com split temporal."""
    path = processed_dir / DATASET_PARQUET
    if not path.is_file():
        raise FileNotFoundError(
            f"Arquivo nao encontrado: {path}. "
            "Execute python -m src.application.build_dataset antes do treino"
        )
    frame = pd.read_parquet(path)
    _validate_dataset(frame)
    return frame


def _validate_dataset(frame: pd.DataFrame) -> None:
    """Garante colunas minimas para treino."""
    required = {*FEATURE_COLUMNS, TARGET_COLUMN, SPLIT_COLUMN}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Dataset sem colunas obrigatorias: {sorted(missing)}")
    if frame.empty:
        raise ValueError("Dataset vazio para treino")


def _split_train_test(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Separa linhas por coluna split gerada em S2.E3."""
    train_df = frame[frame[SPLIT_COLUMN] == "train"].copy()
    test_df = frame[frame[SPLIT_COLUMN] == "test"].copy()
    if train_df.empty or test_df.empty:
        raise ValueError("Dataset precisa de linhas em train e test")
    return train_df, test_df


def extract_xy(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Extrai matriz de features e vetor alvo."""
    x_frame = frame.loc[:, FEATURE_COLUMNS].apply(pd.to_numeric, errors="coerce")
    y_series = frame[TARGET_COLUMN].astype(int)
    return x_frame, y_series


def tune_lgbm_params(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
) -> tuple[dict[str, object], float | None]:
    """Seleciona hiperparametros pelo maior AUC no conjunto de teste."""
    x_train, y_train = extract_xy(train_df)
    x_test, y_test = extract_xy(test_df)
    scale_pos_weight = _scale_pos_weight(y_train)

    best_params: dict[str, object] = {}
    best_auc: float | None = None
    total = len(CANDIDATE_PARAM_SETS)

    for index, candidate in enumerate(CANDIDATE_PARAM_SETS, start=1):
        label = candidate or DEFAULT_LGBM_PARAMS
        print(f"Tuning {index}/{total}: {label}", flush=True)
        model = _fit_classifier_arrays(
            x_train,
            y_train,
            x_test,
            y_test,
            params=candidate,
            scale_pos_weight=scale_pos_weight,
        )
        proba = model.predict_proba(x_test)[:, 1]
        auc = _roc_auc(y_test.to_numpy(), proba)
        print(f"  AUC teste={auc}", flush=True)
        if auc is not None and (best_auc is None or auc > best_auc):
            best_auc = auc
            best_params = candidate

    print(f"Melhor tuning AUC={best_auc} params={best_params or 'default'}", flush=True)
    return best_params, best_auc


def _fit_classifier(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    params: dict[str, object] | None = None,
) -> lgb.LGBMClassifier:
    """Ajusta LightGBM com peso para classes desbalanceadas."""
    x_train, y_train = extract_xy(train_df)
    x_test, y_test = extract_xy(test_df)
    return _fit_classifier_arrays(
        x_train,
        y_train,
        x_test,
        y_test,
        params=params or {},
        scale_pos_weight=_scale_pos_weight(y_train),
    )


def _fit_classifier_arrays(
    x_train: pd.DataFrame,
    y_train: pd.Series,
    x_test: pd.DataFrame,
    y_test: pd.Series,
    *,
    params: dict[str, object],
    scale_pos_weight: float,
) -> lgb.LGBMClassifier:
    """Treina classificador com early stopping no holdout."""
    model = lgb.LGBMClassifier(
        **_merge_lgbm_params(params),
        scale_pos_weight=scale_pos_weight,
    )
    fit_kwargs: dict[str, object] = {}
    if y_train.nunique() > 1 and y_test.nunique() > 0:
        fit_kwargs["eval_set"] = [(x_test, y_test)]
        fit_kwargs["eval_metric"] = "auc"
        fit_kwargs["callbacks"] = [lgb.early_stopping(stopping_rounds=20, verbose=False)]

    model.fit(x_train, y_train, **fit_kwargs)
    return model


def _scale_pos_weight(y_train: pd.Series) -> float:
    """Peso da classe positiva para desbalanceamento."""
    positives = int(y_train.sum())
    negatives = len(y_train) - positives
    return negatives / positives if positives > 0 else 1.0


def _merge_lgbm_params(params: dict[str, object]) -> dict[str, object]:
    """Mescla defaults com candidato de tuning."""
    return {**DEFAULT_LGBM_PARAMS, **params}


def _resolved_lgbm_params(
    params: dict[str, object],
    train_df_or_y: pd.DataFrame | pd.Series,
) -> dict[str, object]:
    """Params finais persistidos em metrics.json."""
    if isinstance(train_df_or_y, pd.DataFrame):
        _, y_train = extract_xy(train_df_or_y)
    else:
        y_train = train_df_or_y
    resolved = _merge_lgbm_params(params)
    resolved["scale_pos_weight"] = round(_scale_pos_weight(y_train), 4)
    return resolved


def _evaluate_model(
    model: lgb.LGBMClassifier,
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
) -> dict[str, object]:
    """Calcula metricas no holdout temporal."""
    _, y_train = extract_xy(train_df)
    x_test, y_test = extract_xy(test_df)
    proba = model.predict_proba(x_test)[:, 1]
    test_metrics = _binary_metrics(y_test.to_numpy(), proba)

    return {
        "model": "lightgbm",
        "target": TARGET_COLUMN,
        "feature_columns": list(FEATURE_COLUMNS),
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "train_rows": len(train_df),
        "test_rows": len(test_df),
        "train_positive_rate": round(float(y_train.mean()), 6),
        "test_positive_rate": round(float(y_test.mean()), 6),
        "best_iteration": int(getattr(model, "best_iteration_", model.n_estimators)),
        **test_metrics,
    }


def _binary_metrics(y_true: np.ndarray, proba: np.ndarray, threshold: float = 0.5) -> dict[str, object]:
    """Metricas de classificacao binaria sem dependencia de sklearn."""
    y_pred = (proba >= threshold).astype(int)
    tp = int(((y_pred == 1) & (y_true == 1)).sum())
    tn = int(((y_pred == 0) & (y_true == 0)).sum())
    fp = int(((y_pred == 1) & (y_true == 0)).sum())
    fn = int(((y_pred == 0) & (y_true == 1)).sum())

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    accuracy = (tp + tn) / len(y_true) if len(y_true) else 0.0
    roc_auc = _roc_auc(y_true, proba)

    return {
        "threshold": threshold,
        "roc_auc": None if roc_auc is None else round(roc_auc, 6),
        "accuracy": round(accuracy, 6),
        "precision": round(precision, 6),
        "recall": round(recall, 6),
        "f1": round(f1, 6),
        "confusion": {"tp": tp, "tn": tn, "fp": fp, "fn": fn},
    }


def _roc_auc(y_true: np.ndarray, scores: np.ndarray) -> float | None:
    """AUC-ROC por rank (Mann-Whitney), sem sklearn."""
    positives = int(y_true.sum())
    negatives = len(y_true) - positives
    if positives == 0 or negatives == 0:
        return None

    order = np.argsort(scores)
    ranks = np.empty(len(scores), dtype=float)
    ranks[order] = np.arange(1, len(scores) + 1)

    pos_rank_sum = ranks[y_true == 1].sum()
    return float((pos_rank_sum - positives * (positives + 1) / 2) / (positives * negatives))


def _save_model(models_dir: Path, model: lgb.LGBMClassifier) -> Path:
    """Serializa modelo treinado em pickle."""
    models_dir.mkdir(parents=True, exist_ok=True)
    path = models_dir / MODEL_FILENAME
    with path.open("wb") as handle:
        pickle.dump(model, handle)
    return path


def _save_metrics(models_dir: Path, metrics: dict[str, object]) -> Path:
    """Grava metricas de avaliacao em JSON."""
    models_dir.mkdir(parents=True, exist_ok=True)
    path = models_dir / METRICS_FILENAME
    path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return path


def main() -> None:
    """Entrypoint: python -m src.infrastructure.ml.train"""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    report = train_model()
    print(
        f"Treino: train={report.train_rows} test={report.test_rows} "
        f"auc={report.metrics.get('roc_auc')} "
        f"model={report.model_path} metrics={report.metrics_path} "
        f"confusion={report.confusion_matrix_path}"
    )


if __name__ == "__main__":
    main()
